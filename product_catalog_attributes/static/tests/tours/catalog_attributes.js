/** @odoo-module */
import { registry } from "@web/core/registry";

const attributeSection = '.o_search_panel_section:has(.o_catalog_attributes_actions)';
const choice = (name) => `${attributeSection} .o_search_panel_filter_value:contains("${name}") input`;
const cards = '.o_kanban_renderer';

registry.category("web_tour.tours").add("catalog_attribute_filters", {
    steps: () => [
        { trigger: '.o_form_view button[name="action_add_from_catalog"]', run: 'click' },
        { trigger: '.o_searchview_input', run: 'edit Facet Tour' },
        { trigger: '.o_searchview_input', run: 'press Enter' },
        { trigger: `${cards} .o_kanban_record:contains("Facet Tour Alpha")` },
        { trigger: choice('Facet Acme'), run: 'click' },
        { trigger: `${cards}:not(:has(.o_kanban_record:contains("Facet Tour Beta")))` },
        { trigger: choice('Facet Other'), run: 'click' },
        { trigger: `${cards} .o_kanban_record:contains("Facet Tour Beta")` },
        { trigger: choice('Facet Other'), run: 'click' },
        { trigger: choice('Facet 12000'), run: 'click' },
        { trigger: `${cards}:not(:has(.o_kanban_record:contains("Facet Tour Alpha"))):not(:has(.o_kanban_record:contains("Facet Tour Beta")))` },
        { trigger: `${cards} .o_kanban_record:contains("Facet Tour Gamma") .fa-shopping-cart`, run: 'click' },
        { trigger: `${cards} .o_kanban_record:contains("Facet Tour Gamma"):not(:has(.fa-shopping-cart))` },
        { trigger: '.o_searchview_facet .o_facet_remove', run: 'click' },
        { trigger: '.o_searchview_input', run: 'edit NoSuchFacetProduct12345' },
        { trigger: '.o_searchview_input', run: 'press Enter' },
        { trigger: '.o_view_nocontent' },
        { trigger: `${attributeSection} input:checked` },
        { trigger: '.o_searchview_facet:last .o_facet_remove', run: 'click' },
        { trigger: '.o_searchview_input', run: 'edit Facet Tour' },
        { trigger: '.o_searchview_input', run: 'press Enter' },
        { trigger: `${cards} .o_kanban_record:contains("Facet Tour Gamma")` },
        { trigger: '.o_catalog_attributes_actions button:contains("Clear attributes")', run: 'click' },
        { trigger: `${cards} .o_kanban_record:contains("Facet Tour Alpha")` },
        { trigger: `${cards} .o_kanban_record:contains("Facet Tour Beta")` },
        { trigger: '.o_searchview_facet .o_facet_remove', run: 'click' },
        { trigger: '.o_searchview_input', run: 'edit Facet Tour Empty' },
        { trigger: '.o_searchview_input', run: 'press Enter' },
        { trigger: '.o_catalog_attributes_actions:contains("No attributes for these products")' },
        { trigger: '.o-kanban-button-back', run: 'click' },
        { trigger: '.o_form_view .o_data_row:contains("Facet Tour Gamma")' },
    ],
});
