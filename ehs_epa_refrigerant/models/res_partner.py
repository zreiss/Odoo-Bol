from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

from .epa_credential import EDITABLE_FIELDS, FILE_FIELDS, STATUS_LABELS


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _epa_account(self):
        self.ensure_one()
        self.env['ehs.epa.credential']._check_epa_user()
        self.check_access('write')
        account = self.commercial_partner_id
        account.check_access('write')
        return account

    def _epa_current(self):
        account = self._epa_account()
        return self.env['ehs.epa.credential'].search([
            ('partner_id', '=', account.id), ('company_id', '=', self.env.company.id),
            ('current', '=', True),
        ], limit=1)

    def epa_account_data(self):
        account = self._epa_account()
        current = self._epa_current()
        data = {
            'account_id': account.id, 'account_name': account.display_name,
            'is_company': account.is_company, 'company_name': self.env.company.name,
            'status': current.state or 'missing',
            'status_label': _(STATUS_LABELS.get(current.state, STATUS_LABELS['missing'])),
            'credential_id': current.id or False, 'values': {}, 'files': {},
            'verified_by': current.verified_by.name or '',
            'verified_at': fields.Datetime.to_string(current.verified_at) or '',
            'change_reason': current.change_reason or '',
            'can_manage': self.env.su or self.env.user.has_group('ehs_epa_refrigerant.group_epa_manager'),
        }
        if current:
            data['values'] = {
                name: current[name] or '' for name in EDITABLE_FIELDS
                if name not in FILE_FIELDS and name not in {field + '_name' for field in FILE_FIELDS}
            }
            for name in FILE_FIELDS:
                data['files'][name] = {
                    'present': bool(current.with_context(bin_size=True)[name]),
                    'name': current[name + '_name'] or _('Uploaded evidence'),
                }
        return data

    def epa_save_account(self, values):
        account = self._epa_account()
        if not isinstance(values, dict) or set(values) - EDITABLE_FIELDS:
            raise AccessError(_('Only EPA account entry fields can be saved here.'))
        self.env.cr.execute('SELECT id FROM res_partner WHERE id = %s FOR UPDATE', [account.id])
        current = self._epa_current()
        if current:
            current.write(values)
        else:
            current = self.env['ehs.epa.credential'].create({
                **values, 'partner_id': account.id, 'company_id': self.env.company.id,
            })
        return current.id

    def epa_verify_account(self):
        self._epa_current().action_verify()
        return True

    def epa_change_account(self, operation, reason):
        current = self._epa_current()
        if operation == 'withdraw':
            current.action_withdraw(reason)
        elif operation == 'replace':
            current.action_replace(reason)
        else:
            raise ValidationError(_('Choose Withdraw or Replace.'))
        return True

    def write(self, vals):
        if {'parent_id', 'is_company', 'company_id'} & set(vals):
            for partner in self:
                changing = any(
                    (partner[name].id if name in ('parent_id', 'company_id') else partner[name]) != value
                    for name, value in vals.items() if name in ('parent_id', 'is_company', 'company_id')
                )
                if changing and self.env['ehs.epa.credential'].sudo().search_count([
                    ('partner_id', '=', partner.id),
                ]):
                    raise UserError(_(
                        'This account has retained EPA files. Keep its company/account ownership unchanged; '
                        'use a separate customer account for a different legal entity.'
                    ))
        return super().write(vals)
