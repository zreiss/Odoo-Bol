import json

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestCatalogAttributes(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Product = cls.env['product.product']
        cls.brand = cls.env['product.attribute'].create({
            'name': 'Catalog Test Brand', 'create_variant': 'no_variant',
        })
        cls.capacity = cls.env['product.attribute'].create({
            'name': 'Catalog Test Capacity', 'create_variant': 'no_variant',
        })
        cls.color = cls.env['product.attribute'].create({'name': 'Catalog Test Color'})
        cls.acme, cls.other = cls.env['product.attribute.value'].create([
            {'name': 'Acme', 'attribute_id': cls.brand.id},
            {'name': 'Other', 'attribute_id': cls.brand.id},
        ])
        cls.small, cls.large = cls.env['product.attribute.value'].create([
            {'name': '9000', 'attribute_id': cls.capacity.id},
            {'name': '12000', 'attribute_id': cls.capacity.id},
        ])
        cls.red, cls.blue = cls.env['product.attribute.value'].create([
            {'name': 'Red', 'attribute_id': cls.color.id},
            {'name': 'Blue', 'attribute_id': cls.color.id},
        ])
        cls.category = cls.env['product.category'].create({'name': 'Catalog Facet Tests'})
        cls.first = cls._make_template('Facet Test A', [cls.acme, cls.small])
        cls.second = cls._make_template('Facet Test B', [cls.other, cls.large])
        cls.variant_template = cls._make_template('Facet Test C', [cls.acme, cls.red | cls.blue])
        cls.products = (cls.first | cls.second | cls.variant_template).product_variant_ids
        cls.user = new_test_user(cls.env, login='catalog_facet_employee', groups='base.group_user')

    @classmethod
    def _make_template(cls, name, choices, **extra):
        return cls.env['product.template'].create({
            'name': name, 'categ_id': cls.category.id,
            'attribute_line_ids': [Command.create({
                'attribute_id': values.attribute_id.id,
                'value_ids': [Command.set(values.ids)],
            }) for values in choices],
            **extra,
        })

    def _facets(self, **kwargs):
        return self.Product.search_panel_select_multi_range(
            'catalog_attribute_value_ids',
            search_domain=[('id', 'in', self.products.ids)],
            group_by='attribute_id', enable_counters=True, **kwargs,
        )['values']

    def test_descriptive_and_variant_values(self):
        first_variant = self.first.product_variant_id
        self.assertFalse(first_variant.product_template_attribute_value_ids)
        self.assertEqual(first_variant.catalog_attribute_value_ids, self.acme | self.small)
        red_product = self.variant_template.product_variant_ids.filtered(
            lambda product: self.red in product.catalog_attribute_value_ids)
        self.assertEqual(len(red_product), 1)
        self.assertNotIn(self.blue, red_product.catalog_attribute_value_ids)
        matching = self.Product.search([
            ('id', 'in', self.products.ids),
            ('catalog_attribute_value_ids', 'in', [self.red.id]),
        ])
        self.assertEqual(matching, red_product)

    def test_or_within_and_between_attributes(self):
        matches = self.Product.search([
            ('id', 'in', self.products.ids),
            ('catalog_attribute_value_ids', 'in', (self.acme | self.other).ids),
            ('catalog_attribute_value_ids', 'in', self.large.ids),
        ])
        self.assertEqual(matches, self.second.product_variant_id)

    def test_unique_global_values_and_counts(self):
        facets = self._facets()
        self.assertEqual(len({value['id'] for value in facets}), len(facets))
        by_id = {value['id']: value for value in facets}
        self.assertEqual(by_id[self.acme.id]['__count'], 3)
        self.assertEqual(by_id[self.red.id]['__count'], 1)
        self.assertEqual(by_id[self.acme.id]['display_name'], 'Acme')
        self.assertEqual(by_id[self.acme.id]['group_name'], self.brand.name)

    def test_search_and_category_limit_relevance(self):
        result = self.Product.search_panel_select_multi_range(
            'catalog_attribute_value_ids', search_domain=[('name', '=', self.first.name)],
            category_domain=[('categ_id', '=', self.category.id)],
            enable_counters=True, group_by='attribute_id',
        )['values']
        self.assertEqual({value['id'] for value in result}, set((self.acme | self.small).ids))
        self.assertEqual(self._facets(category_domain=[('categ_id', '=', -1)]), [])

    def test_other_filters_and_attribute_counters(self):
        facets = self._facets(
            group_domain={json.dumps(self.capacity.id): [
                ('catalog_attribute_value_ids', 'in', self.other.ids),
            ]},
        )
        by_id = {value['id']: value for value in facets}
        self.assertEqual(by_id[self.small.id]['__count'], 0)
        self.assertEqual(by_id[self.large.id]['__count'], 1)
        values = self._facets(filter_domain=[('id', '=', self.first.product_variant_id.id)])
        self.assertEqual({value['id'] for value in values}, set((self.acme | self.small).ids))

    def test_empty_and_archived_products(self):
        self.products.active = False
        self.assertEqual(self._facets(), [])

    def test_archived_values_attributes_and_lines(self):
        self.acme.active = False
        self.assertNotIn(self.acme.id, {value['id'] for value in self._facets()})
        self.assertFalse(self.Product.search([
            ('id', 'in', self.products.ids), ('catalog_attribute_value_ids', 'in', self.acme.ids),
        ]))
        self.capacity.active = False
        self.assertNotIn(self.large.id, {value['id'] for value in self._facets()})
        self.variant_template.attribute_line_ids.filtered(
            lambda line: line.attribute_id == self.brand).active = False
        self.assertNotIn(self.acme, self.variant_template.product_variant_ids.catalog_attribute_value_ids)

    def test_negative_search_is_complement(self):
        positives = self.Product.search([
            ('id', 'in', self.products.ids), ('catalog_attribute_value_ids', 'in', self.acme.ids),
        ])
        negatives = self.Product.search([
            ('id', 'in', self.products.ids), ('catalog_attribute_value_ids', 'not in', self.acme.ids),
        ])
        self.assertEqual(negatives, self.products - positives)

    def test_access_rules_and_company(self):
        company = self.env['res.company'].create({'name': 'Other Facet Company'})
        private = self._make_template('Private Facet Product', [self.other], company_id=company.id)
        result = self.Product.with_user(self.user).search_panel_select_multi_range(
            'catalog_attribute_value_ids',
            search_domain=[('id', 'in', (private.product_variant_ids | self.first.product_variant_ids).ids)],
            group_by='attribute_id', enable_counters=True,
        )['values']
        self.assertEqual({value['id'] for value in result}, set((self.acme | self.small).ids))
        self.env['ir.rule'].create({
            'name': 'Hide first facet fixture',
            'model_id': self.env['ir.model']._get_id('product.product'),
            'domain_force': repr([('id', '!=', self.first.product_variant_id.id)]),
        })
        result = self.Product.with_user(self.user).search_panel_select_multi_range(
            'catalog_attribute_value_ids',
            search_domain=[('id', '=', self.first.product_variant_id.id)],
            group_by='attribute_id', enable_counters=True,
        )['values']
        self.assertEqual(result, [])

    def test_no_product_changes_when_filtering(self):
        before = self.products.read([
            'active', 'default_code', 'list_price', 'standard_price',
            'product_template_attribute_value_ids', 'write_date',
        ])
        self._facets()
        self.assertEqual(self.products.read([
            'active', 'default_code', 'list_price', 'standard_price',
            'product_template_attribute_value_ids', 'write_date',
        ]), before)

    def test_other_searchpanel_sections_unchanged(self):
        categories = self.Product.search_panel_select_range(
            'categ_id', search_domain=[('id', 'in', self.products.ids)],
        )
        self.assertIn(self.category.id, {value['id'] for value in categories['values']})
        tags = self.Product.search_panel_select_multi_range(
            'product_tag_ids', search_domain=[('id', 'in', self.products.ids)],
        )
        self.assertIn('values', tags)

    def test_public_cannot_read_facets(self):
        with self.assertRaises(AccessError):
            self.Product.with_user(self.env.ref('base.public_user')).search_panel_select_multi_range(
                'catalog_attribute_value_ids', search_domain=[('id', 'in', self.products.ids)],
            )
