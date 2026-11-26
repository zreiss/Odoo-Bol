import base64
import binascii

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.mimetypes import guess_mimetype


FILE_FIELDS = ('certificate_front', 'certificate_back', 'employer_proof')
EDITABLE_FIELDS = {
    'declaration', 'credential_type', 'number', 'technician_name',
    'certificate_front', 'certificate_front_name', 'certificate_back',
    'certificate_back_name', 'employer_proof', 'employer_proof_name',
    'authorized_buyers', 'notes', 'scope_reviewed',
}
STATUS_LABELS = {
    'missing': 'Missing information',
    'draft': 'Needs review',
    'verified': 'Verified account file',
    'withdrawn': 'Withdrawn',
    'superseded': 'Superseded',
}


def validate_evidence(value, translate=lambda message: message):
    if not value:
        return
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise ValidationError(translate('Upload a readable JPG, PNG, or PDF file.')) from None
    if not raw or len(raw) > 10 * 1024 * 1024:
        raise ValidationError(translate('Each evidence file must be nonempty and no larger than 10 MB.'))
    if guess_mimetype(raw) not in ('image/jpeg', 'image/png', 'application/pdf'):
        raise ValidationError(translate('Only JPG, PNG, and PDF evidence files are accepted.'))


class EpaCredential(models.Model):
    _name = 'ehs.epa.credential'
    _description = 'EPA 608 Account Certification Version'
    _order = 'id desc'
    _check_company_auto = True

    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', index=True)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company, index=True,
    )
    current = fields.Boolean(default=True, readonly=True)
    declaration = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Has EPA 608 certification?')
    credential_type = fields.Selection([
        ('i', 'I'), ('ii', 'II'), ('iii', 'III'), ('universal', 'Universal'),
    ], string='Certification type')
    number = fields.Char(string='License number')
    technician_name = fields.Char(string='Certified technician name')
    certificate_front = fields.Binary(attachment=True)
    certificate_front_name = fields.Char()
    certificate_back = fields.Binary(attachment=True)
    certificate_back_name = fields.Char()
    employer_proof = fields.Binary(attachment=True)
    employer_proof_name = fields.Char()
    employer_required = fields.Boolean(readonly=True)
    scope_reviewed = fields.Boolean(string='Certification scope and supporting proof reviewed')
    authorized_buyers = fields.Text()
    notes = fields.Text()
    state = fields.Selection([
        ('draft', 'Needs review'), ('verified', 'Verified account file'),
        ('withdrawn', 'Withdrawn'), ('superseded', 'Superseded'),
    ], default='draft', required=True, readonly=True)
    verified_by = fields.Many2one('res.users', readonly=True, ondelete='restrict')
    verified_at = fields.Datetime(readonly=True)
    changed_by = fields.Many2one('res.users', readonly=True, ondelete='restrict')
    changed_at = fields.Datetime(readonly=True)
    change_reason = fields.Text(readonly=True)

    _current_account_unique = models.UniqueIndex(
        '(partner_id, company_id) WHERE current',
        'This account already has a current EPA file for this company.',
    )

    @api.model
    def _check_epa_user(self, manager=False):
        group = 'group_epa_manager' if manager else 'group_epa_user'
        if not self.env.su and not self.env.user.has_group('ehs_epa_refrigerant.' + group):
            raise AccessError(_('You do not have permission to manage EPA account records.'))

    def _lock(self):
        self.flush_recordset()
        self.env.cr.execute(
            'SELECT id FROM ehs_epa_credential WHERE id IN %s ORDER BY id FOR UPDATE',
            [tuple(self.ids)],
        )
        self.invalidate_recordset()

    @api.model_create_multi
    def create(self, vals_list):
        self._check_epa_user()
        cleaned = []
        for incoming in vals_list:
            vals = dict(incoming)
            if set(vals) - EDITABLE_FIELDS - {'partner_id', 'company_id'}:
                raise AccessError(_('Review status can only be changed through EPA review actions.'))
            partner = self.env['res.partner'].browse(vals.get('partner_id')).exists()
            partner.check_access('write')
            if not partner or partner.commercial_partner_id != partner:
                raise ValidationError(_('Keep the license on the main customer or company account.'))
            company_id = vals.get('company_id') or self.env.company.id
            if company_id not in self.env.companies.ids:
                raise AccessError(_('Select a company you are allowed to use.'))
            if partner.company_id and partner.company_id.id != company_id:
                raise ValidationError(_('The customer belongs to a different company.'))
            for field in FILE_FIELDS:
                validate_evidence(vals.get(field), self.env._)
            vals.update(
                company_id=company_id, employer_required=partner.is_company,
                state='draft', current=True, verified_by=False, verified_at=False,
                changed_by=False, changed_at=False, change_reason=False,
            )
            cleaned.append(vals)
        create_self = self.with_context({
            key: value for key, value in self.env.context.items()
            if not key.startswith('default_')
        })
        return super(EpaCredential, create_self).create(cleaned)

    def write(self, vals):
        self._check_epa_user()
        self.check_access('write')
        if set(vals) - EDITABLE_FIELDS:
            raise AccessError(_('Review status and account ownership cannot be edited directly.'))
        if not self:
            return True
        self._lock()
        if any(record.state != 'draft' or not record.current for record in self):
            raise UserError(_('Reviewed EPA files are retained. Create a replacement version instead.'))
        for field in FILE_FIELDS:
            validate_evidence(vals.get(field), self.env._)
        return super().write(vals)

    def unlink(self):
        raise UserError(_('EPA account files are retained. Withdraw or replace the file instead of deleting it.'))

    def _missing_items(self):
        self.ensure_one()
        missing = []
        if self.declaration != 'yes':
            missing.append(_('EPA 608 certification must be Yes'))
        if not self.credential_type:
            missing.append(_('certification type'))
        if not (self.number or '').strip():
            missing.append(_('license number'))
        if not (self.technician_name or '').strip():
            missing.append(_('certified technician name'))
        if not self.with_context(bin_size=False).certificate_front:
            missing.append(_('license photo or PDF'))
        if self.employer_required and not self.with_context(bin_size=False).employer_proof:
            missing.append(_('employer evidence'))
        if not self.scope_reviewed:
            missing.append(_('staff review of certification scope and supporting proof'))
        return missing

    def action_verify(self):
        self.ensure_one()
        self._check_epa_user()
        self.check_access('write')
        self._lock()
        if self.state != 'draft' or not self.current:
            raise UserError(_('Only the current draft EPA file can be verified.'))
        if self.partner_id.commercial_partner_id != self.partner_id or not self.partner_id.active:
            raise UserError(_('Use an active main customer account before reviewing this file.'))
        for field in FILE_FIELDS:
            validate_evidence(self.with_context(bin_size=False)[field], self.env._)
        missing = self._missing_items()
        if missing:
            raise ValidationError(_('Complete the following before verifying:\n• %s') % '\n• '.join(missing))
        super(EpaCredential, self).write({
            'state': 'verified', 'verified_by': self.env.uid,
            'verified_at': fields.Datetime.now(),
        })
        return True

    def action_withdraw(self, reason):
        self.ensure_one()
        self._check_epa_user(manager=True)
        self.check_access('write')
        self._lock()
        if not (reason or '').strip():
            raise ValidationError(_('Enter the reason for withdrawing this account file.'))
        if self.state != 'verified' or not self.current:
            raise UserError(_('Only the current verified EPA file can be withdrawn.'))
        return super(EpaCredential, self).write({
            'state': 'withdrawn', 'changed_by': self.env.uid,
            'changed_at': fields.Datetime.now(), 'change_reason': reason.strip(),
        })

    def action_replace(self, reason):
        self.ensure_one()
        self._check_epa_user(manager=True)
        self.check_access('write')
        self._lock()
        if not self.current or self.state == 'draft':
            raise UserError(_('Replace the current reviewed or withdrawn EPA file. Drafts can be edited directly.'))
        if not (reason or '').strip():
            raise ValidationError(_('Enter the reason for replacing the account file.'))
        super(EpaCredential, self).write({
            'current': False, 'state': 'superseded', 'changed_by': self.env.uid,
            'changed_at': fields.Datetime.now(), 'change_reason': reason.strip(),
        })
        self.flush_recordset(['current', 'state'])
        return self.create({
            'partner_id': self.partner_id.id, 'company_id': self.company_id.id,
        }).id
