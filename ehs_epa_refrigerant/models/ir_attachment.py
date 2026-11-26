import base64

from odoo import api, models, _
from odoo.exceptions import UserError, ValidationError

from .epa_credential import FILE_FIELDS, validate_evidence


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _epa_protected(self):
        return self.filtered(lambda attachment: attachment.res_model == 'ehs.epa.credential')

    def _epa_check_draft(self):
        for attachment in self._epa_protected():
            credential = self.env['ehs.epa.credential'].sudo().browse(attachment.res_id).exists()
            if credential:
                credential._lock()
            if not credential or credential.state != 'draft' or not credential.current:
                raise UserError(_('Reviewed EPA evidence cannot be changed or deleted. Create a replacement account file.'))

    @api.constrains('public', 'access_token', 'res_model', 'res_id', 'res_field', 'type', 'url')
    def _check_epa_private_file(self):
        for attachment in self._epa_protected():
            if attachment.public or attachment.access_token:
                raise ValidationError(_('EPA evidence must remain private without a sharing token.'))
            if attachment.res_field not in FILE_FIELDS or attachment.type != 'binary' or attachment.url:
                raise ValidationError(_('Upload EPA proof through the dedicated license or employer fields.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('res_model') != 'ehs.epa.credential':
                continue
            credential = self.env['ehs.epa.credential'].sudo().browse(vals.get('res_id')).exists()
            if credential:
                credential._lock()
            if not credential or credential.state != 'draft' or not credential.current:
                raise UserError(_('Evidence can only be uploaded to a current draft EPA file.'))
            if vals.get('res_field') not in FILE_FIELDS or vals.get('type', 'binary') != 'binary':
                raise ValidationError(_('Upload EPA proof through the dedicated license or employer fields.'))
            if vals.get('public') or vals.get('access_token'):
                raise ValidationError(_('EPA evidence must remain private without a sharing token.'))
            if vals.get('datas'):
                validate_evidence(vals['datas'], self.env._)
            if vals.get('raw'):
                validate_evidence(base64.b64encode(vals['raw']), self.env._)
        return super().create(vals_list)

    def write(self, vals):
        protected = self._epa_protected()
        if vals.get('res_model') == 'ehs.epa.credential' and len(protected) != len(self):
            raise ValidationError(_('Existing attachments cannot be relinked into an EPA file. Upload new evidence.'))
        if protected:
            if {'res_model', 'res_id', 'res_field'} & set(vals):
                raise UserError(_('EPA evidence cannot be relinked to another record or field.'))
            if vals.get('public') or vals.get('access_token'):
                raise ValidationError(_('EPA evidence must remain private without a sharing token.'))
            protected._epa_check_draft()
            if vals.get('type', 'binary') != 'binary' or vals.get('url'):
                raise ValidationError(_('Upload a file, not a link, as EPA evidence.'))
            if vals.get('datas'):
                validate_evidence(vals['datas'], self.env._)
            if vals.get('raw'):
                validate_evidence(base64.b64encode(vals['raw']), self.env._)
        return super().write(vals)

    def unlink(self):
        self._epa_check_draft()
        return super().unlink()
