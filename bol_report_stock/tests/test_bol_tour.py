from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestBolPrintMenu(HttpCase):

    def test_bol_print_menu(self):
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        self.start_tour(
            '/odoo/action-stock.action_picking_tree_outgoing/%s' % picking.id,
            'bol_print_menu', login='admin', timeout=120,
        )
