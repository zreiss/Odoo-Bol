/** @odoo-module */
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ehs_epa_account", {
    steps: () => [
        { trigger: '.o_form_view' },
        { trigger: '.o_notebook .nav-link:contains("EPA 608")', run: 'click' },
        { trigger: '.ehs-epa-number', run: 'edit TOUR-UPDATED' },
        { trigger: '.ehs-epa-review', run: 'click' },
        { trigger: '.ehs-epa-verify', run: 'click' },
        { trigger: '.ehs-epa-account [role="alert"]:contains("employer evidence")' },
        { trigger: '.ehs-epa-number', run() {
            if (document.querySelector('.ehs-epa-number').value !== 'TOUR-UPDATED') {
                throw new Error('EPA input was lost after a validation error');
            }
        } },
        { trigger: '.ehs-epa-save', run: 'click' },
        { trigger: '.ehs-epa-account:not(:has([role="status"])) .ehs-epa-save' },
        { trigger: '.o_notebook .nav-link:contains("Contacts")', run: 'click' },
        { trigger: '.ehs-epa-summary:contains("Needs review")' },
    ],
});
