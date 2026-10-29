from collections import Counter
import json

from odoo import api, fields, models
from odoo.fields import Domain


class ProductProduct(models.Model):
    _inherit = 'product.product'

    catalog_attribute_value_ids = fields.Many2many(
        'product.attribute.value', string='Attributes',
        compute='_compute_catalog_attribute_value_ids',
        search='_search_catalog_attribute_value_ids',
    )

    @api.depends(
        'product_template_attribute_value_ids.ptav_active',
        'product_template_attribute_value_ids.product_attribute_value_id.active',
        'product_template_attribute_value_ids.attribute_id.active',
        'product_tmpl_id.attribute_line_ids.active',
        'product_tmpl_id.attribute_line_ids.product_template_value_ids.ptav_active',
        'product_tmpl_id.attribute_line_ids.value_ids.active',
        'product_tmpl_id.attribute_line_ids.attribute_id.active',
        'product_tmpl_id.attribute_line_ids.attribute_id.create_variant',
    )
    def _compute_catalog_attribute_value_ids(self):
        for product in self:
            lines = product.product_tmpl_id.attribute_line_ids.filtered(
                lambda line: line.active and line.attribute_id.create_variant == 'no_variant'
            )
            values = (
                product.product_template_attribute_value_ids | lines.product_template_value_ids
            ).filtered(
                lambda value: value.ptav_active and value.attribute_line_id.active
                and value.attribute_id.active and value.product_attribute_value_id.active
            )
            product.catalog_attribute_value_ids = values.product_attribute_value_id

    def _search_catalog_attribute_value_ids(self, operator, operand):
        if operator != 'in':
            return NotImplemented
        if isinstance(operand, int):
            operand = [operand]
        value_domain = Domain.AND([
            [('product_attribute_value_id', 'in', operand)],
            [('ptav_active', '=', True)],
            [('product_attribute_value_id.active', '=', True)],
            [('attribute_id.active', '=', True)],
            [('attribute_line_id.active', '=', True)],
        ])
        return Domain.OR([
            Domain('product_template_attribute_value_ids', 'any', value_domain),
            Domain('product_tmpl_id.attribute_line_ids.product_template_value_ids', 'any',
                   value_domain & Domain('attribute_id.create_variant', '=', 'no_variant')),
        ])

    @api.model
    def search_panel_select_multi_range(self, field_name, **kwargs):
        if field_name != 'catalog_attribute_value_ids':
            return super().search_panel_select_multi_range(field_name, **kwargs)

        # Start with visible products, not all attribute definitions. No sudo:
        # neither counts nor labels may expose inaccessible product specifications.
        domain = Domain.AND([
            kwargs.get('search_domain', []),
            kwargs.get('category_domain', []),
            kwargs.get('filter_domain', []),
        ])
        products = self.search(domain)
        values = products.catalog_attribute_value_ids
        values &= self.env['product.attribute.value'].search(Domain.AND([
            [('id', 'in', values.ids)], kwargs.get('comodel_domain', []),
        ]))
        groups = values.grouped('attribute_id')
        result = []
        group_domains = kwargs.get('group_domain') or {}
        for attribute, attribute_values in groups.items():
            other_groups = group_domains.get(json.dumps(attribute.id), [])
            matching_products = products
            if other_groups:
                matching_products = self.search(domain & Domain(other_groups))
            counts = Counter(
                value.id
                for product in matching_products
                for value in product.catalog_attribute_value_ids
                if value.attribute_id == attribute
            )
            for value in attribute_values.sorted(lambda value: (value.sequence, value.id)):
                result.append({
                    'id': value.id,
                    'display_name': value.name,
                    'group_id': attribute.id,
                    'group_name': attribute.name,
                    'group_sequence': attribute.sequence,
                    '__count': counts[value.id],
                })
        return {'values': result}
