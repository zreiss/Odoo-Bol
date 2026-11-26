from odoo.tests import HttpCase, tagged

from .test_epa_account import PROOF


@tagged('post_install', '-at_install')
class TestEpaAccountTour(HttpCase):
    def test_account_file_tour(self):
        account = self.env['res.partner'].create({'name': 'EPA Tour Company', 'is_company': True})
        self.env['ehs.epa.credential'].create({
            'partner_id': account.id, 'declaration': 'yes', 'credential_type': 'ii',
            'number': 'TOUR-OLD', 'technician_name': 'Tour Technician',
            'certificate_front': PROOF, 'certificate_front_name': 'license.pdf',
        })
        self.start_tour(
            '/odoo/action-base.action_partner_form/%s' % account.id,
            'ehs_epa_account', login='admin', timeout=150,
        )
