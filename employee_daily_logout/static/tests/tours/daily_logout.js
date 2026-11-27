/** @odoo-module */

import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('employee_daily_logout', {
    steps: () => [
        {
            trigger: '.o_web_client',
            async run() {
                await fetch('/employee-daily-logout-test/expire', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: {}, id: 1 }),
                });
                window.dispatchEvent(new Event('focus'));
            },
        },
        {
            trigger: '.o_error_dialog:contains("Your Odoo session expired")',
        },
    ],
});
