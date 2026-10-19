from lxml import html as lxml_html

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestBolReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'BOL Test Customer',
            'street': '100 Consignee Street',
            'city': 'Newark',
            'zip': '07102',
        })
        cls.picking_type_out = cls.env.ref('stock.picking_type_out')
        cls.product = cls.env['product.product'].create({
            'name': 'BOL Test Product',
            'is_storable': True,
            'weight': 12.5,
        })
        carrier_product = cls.env['product.product'].create({
            'name': 'Test Freight Delivery Charge',
            'type': 'service',
            'categ_id': cls.env.ref('delivery.product_category_deliveries').id,
            'sale_ok': False,
            'purchase_ok': False,
            'list_price': 50,
        })
        cls.carrier = cls.env['delivery.carrier'].create({
            'name': 'Test Freight Co.',
            'delivery_type': 'fixed',
            'integration_level': 'rate',
            'fixed_price': 50,
            'product_id': carrier_product.id,
        })
        cls.stock_user = new_test_user(
            cls.env, login='bol_inventory_user', groups='stock.group_stock_user',
            company_id=cls.env.company.id,
            company_ids=[Command.set(cls.env.company.ids)],
        )

    def _create_delivery(self, confirm=False):
        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.partner_id = self.partner
        with delivery_form.move_ids.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 3
        delivery = delivery_form.save()
        delivery.carrier_id = self.carrier
        delivery.carrier_tracking_ref = 'TRK12345'
        if confirm:
            delivery.action_confirm()
        return delivery

    def _render_bol(self, pickings, user=None):
        report = self.env.ref('bol_report_stock.action_report_bol')
        if user:
            report = report.with_user(user)
        html, _report_type = report._render_qweb_html(
            'bol_report_stock.report_bol', pickings.ids)
        return html.decode('utf-8')

    def test_bol_rendered_content(self):
        delivery = self._create_delivery(confirm=True)
        html = self._render_bol(delivery)
        for text in (
            'BILL OF LADING', 'BOL Test Customer', 'Test Freight Co.',
            'TRK12345', 'BOL Test Product', 'PRELIMINARY',
            'Carrier / driver signature', 'Receiver signature',
        ):
            self.assertIn(text, html)
        # Reservation quantities must not masquerade as shipped quantities.
        tree = lxml_html.fromstring(html)
        qty = tree.xpath('//td[@name="bol_quantity"]')[0].text_content().strip()
        self.assertEqual(qty, '3')

    def test_bol_missing_freight_data(self):
        self.product.weight = 0
        delivery = self._create_delivery()
        delivery.carrier_id = False
        delivery.carrier_tracking_ref = False
        html = self._render_bol(delivery)
        tree = lxml_html.fromstring(html)
        self.assertIn('confirm count', tree.xpath('//td[@name="bol_package_count"]')[0].text_content())
        self.assertIn('confirm weight', tree.xpath('//td[@name="bol_weight"]')[0].text_content())

    def test_bol_multiple_shipments(self):
        deliveries = self._create_delivery(confirm=True) | self._create_delivery(confirm=True)
        tree = lxml_html.fromstring(self._render_bol(deliveries))
        self.assertEqual(len(tree.xpath('//div[contains(@class, "bol-document")]')), 2)
        self.assertEqual(len(tree.xpath('//main')), 1)

    def test_bol_pdf_layout_retains_freight_columns(self):
        delivery = self._create_delivery()
        report = self.env.ref('bol_report_stock.action_report_bol')
        html, _report_type = report._render_qweb_html(
            'bol_report_stock.report_bol', delivery.ids, data={'report_type': 'pdf'})
        tree = lxml_html.fromstring(html)
        self.assertEqual(len(tree.xpath('//div[contains(@class, "bol-pdf")]')), 1)
        self.assertFalse(tree.xpath('//div[contains(@class, "bol-html-preview")]'))
        self.assertIn('NMFC', tree.text_content())
        self.assertIn('Class', tree.text_content())

    def test_bol_binding(self):
        report = self.env.ref('bol_report_stock.action_report_bol')
        self.assertEqual(report.model, 'stock.picking')
        self.assertEqual(report.binding_type, 'report')
        self.assertEqual(report.binding_model_id.model, 'stock.picking')
        self.assertEqual(report.paperformat_id.format, 'Letter')

    def test_bol_empty_delivery(self):
        delivery = self._create_delivery()
        delivery.move_ids.unlink()
        delivery.partner_id = False
        html = self._render_bol(delivery)
        self.assertIn('No goods to list.', html)
        self.assertIn('Not specified', html)

    def test_bol_completed_partial(self):
        delivery = self._create_delivery(confirm=True)
        delivery.move_ids.quantity = 2
        delivery.move_ids.picked = True
        delivery.with_context(skip_backorder=True).button_validate()
        self.assertEqual(delivery.state, 'done')
        self.assertTrue(delivery.backorder_ids)
        html = self._render_bol(delivery)
        tree = lxml_html.fromstring(html)
        self.assertNotIn('PRELIMINARY', html)
        self.assertEqual(tree.xpath('//td[@name="bol_quantity"]')[0].text_content().strip(), '2')
        self.assertIn('PRELIMINARY', self._render_bol(delivery.backorder_ids))

    def test_bol_cancelled_lines_excluded(self):
        delivery = self._create_delivery(confirm=True)
        other_product = self.env['product.product'].create({
            'name': 'Cancelled BOL Product', 'is_storable': True,
        })
        cancelled_move = self.env['stock.move'].create({
            'product_id': other_product.id,
            'product_uom': other_product.uom_id.id,
            'product_uom_qty': 1,
            'picking_id': delivery.id,
            'location_id': delivery.location_id.id,
            'location_dest_id': delivery.location_dest_id.id,
        })
        cancelled_move._action_cancel()
        self.assertNotIn('Cancelled BOL Product', self._render_bol(delivery))

    def test_bol_archived_product(self):
        delivery = self._create_delivery()
        self.product.active = False
        self.assertIn('BOL Test Product', self._render_bol(delivery))

    def test_bol_invalid_selection(self):
        delivery = self._create_delivery()
        delivery.action_cancel()
        with self.assertRaisesRegex(UserError, 'not cancelled'):
            self._render_bol(delivery)
        incoming = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
        })
        with self.assertRaisesRegex(UserError, 'outgoing deliveries'):
            self._render_bol(incoming)
        with self.assertRaisesRegex(UserError, 'Select at least one'):
            self._render_bol(self.env['stock.picking'])

    def test_bol_inventory_user(self):
        delivery = self._create_delivery()
        self.assertIn('BOL Test Customer', self._render_bol(delivery, self.stock_user))

    def test_bol_multi_company(self):
        company = self.env['res.company'].create({'name': 'Other BOL Company'})
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
        delivery = self.env['stock.picking'].with_company(company).create({
            'picking_type_id': warehouse.out_type_id.id,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'partner_id': self.partner.id,
        })
        html = self._render_bol(self._create_delivery() | delivery)
        tree = lxml_html.fromstring(html)
        pages = tree.xpath('//div[contains(@class, "bol-document")]')
        self.assertNotIn('Other BOL Company', pages[0].text_content())
        self.assertIn('Other BOL Company', pages[1].text_content())
        with self.assertRaises(AccessError):
            self._render_bol(delivery, self.stock_user)
