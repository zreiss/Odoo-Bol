from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestCatalogAttributeTour(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        brand = cls.env['product.attribute'].create({
            'name': 'Facet Tour Brand', 'create_variant': 'no_variant',
        })
        capacity = cls.env['product.attribute'].create({
            'name': 'Facet Tour BTU', 'create_variant': 'no_variant',
        })
        acme, other, small, large = cls.env['product.attribute.value'].create([
            {'name': 'Facet Acme', 'attribute_id': brand.id},
            {'name': 'Facet Other', 'attribute_id': brand.id},
            {'name': 'Facet 9000', 'attribute_id': capacity.id},
            {'name': 'Facet 12000', 'attribute_id': capacity.id},
        ])
        category = cls.env['product.category'].create({'name': 'Facet Tour Category'})
        cls.templates = cls.env['product.template']
        for suffix, brand_value, capacity_value in [
            ('Alpha', acme, small), ('Beta', other, large), ('Gamma', acme, large),
        ]:
            cls.templates |= cls.env['product.template'].create({
                'name': f'Facet Tour {suffix}', 'categ_id': category.id,
                'list_price': 123,
                'attribute_line_ids': [
                    Command.create({'attribute_id': brand.id, 'value_ids': [Command.set(brand_value.ids)]}),
                    Command.create({'attribute_id': capacity.id, 'value_ids': [Command.set(capacity_value.ids)]}),
                ],
            })
        cls.env['product.template'].create({'name': 'Facet Tour Empty', 'sale_ok': True})
        partner = cls.env['res.partner'].create({'name': 'Facet Tour Customer'})
        cls.order = cls.env['sale.order'].create({'partner_id': partner.id})

    def test_catalog_attribute_tour(self):
        self.start_tour(
            f'/odoo/action-sale.action_quotations_with_onboarding/{self.order.id}',
            'catalog_attribute_filters', login='admin', timeout=180,
        )
        self.assertEqual(self.order.order_line.product_id, self.templates[2].product_variant_id)
        self.assertEqual(self.order.order_line.product_uom_qty, 1)
        self.assertEqual(self.order.order_line.price_unit, 123)
        self.assertEqual(self.order.state, 'draft')
