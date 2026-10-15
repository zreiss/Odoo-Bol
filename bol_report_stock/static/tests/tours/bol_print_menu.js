/** @odoo-module */
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("bol_print_menu", {
    steps: () => [
        {
            trigger: '.o_form_view',
        },
        {
            trigger: 'button[aria-label="Actions menu"]',
            run: 'click',
        },
        {
            trigger: '.o-dropdown--menu button:contains("Print")',
            run: 'click',
        },
        {
            trigger: '.o-dropdown-item:contains("Bill of Lading")',
        },
        {
            trigger: '.o-dropdown-item:contains("Delivery Slip")',
        },
    ],
});
