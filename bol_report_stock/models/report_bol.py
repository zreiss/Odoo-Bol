from odoo import models
from odoo.exceptions import UserError


class ReportBol(models.AbstractModel):
    _name = 'report.bol_report_stock.report_bol'
    _description = 'Bill of Lading Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['stock.picking'].browse(docids)
        docs.check_access('read')
        if not docs:
            raise UserError(self.env._('Select at least one delivery to print a Bill of Lading.'))
        if any(picking.picking_type_code != 'outgoing' or picking.state == 'cancel' for picking in docs):
            raise UserError(self.env._(
                'Bills of Lading are available only for outgoing deliveries that are not cancelled. '
                'Select delivery records and try again.'
            ))
        return {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'docs': docs,
        }
