/** @odoo-module */

import { browser } from '@web/core/browser/browser';
import { SessionExpiredDialog } from '@web/core/errors/error_dialogs';
import { ConnectionLostError, rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { session } from '@web/session';

export const dailyLogoutService = {
    dependencies: ['dialog'],
    start(env, { dialog }) {
        if (!session.employee_daily_logout) {
            return;
        }
        let timer;
        let checking = false;
        let expired = false;
        let deadline;

        function schedule(policy) {
            deadline = browser.performance.now() + Math.max(0, policy.next_cutoff - policy.server_now) * 1000;
            browser.clearTimeout(timer);
            timer = browser.setTimeout(check, Math.max(0, deadline - browser.performance.now()) + 100);
        }

        async function check() {
            if (checking || expired) {
                return;
            }
            checking = true;
            try {
                // Another tab may already have signed in again. Check the shared
                // server session rather than logging out that new session.
                const info = await rpc('/web/session/get_session_info', {}, { silent: true });
                if (info.employee_daily_logout) {
                    schedule(info.employee_daily_logout);
                }
            } catch (error) {
                if (error.data?.name === 'odoo.http.SessionExpiredException') {
                    expired = true;
                    dialog.add(SessionExpiredDialog, {});
                } else if (error instanceof ConnectionLostError) {
                    timer = browser.setTimeout(check, 30000);
                } else {
                    throw error;
                }
            } finally {
                checking = false;
            }
        }

        function checkWhenDue() {
            if (browser.performance.now() >= deadline) {
                check();
            }
        }

        schedule(session.employee_daily_logout);
        browser.addEventListener('focus', checkWhenDue);
        browser.addEventListener('online', checkWhenDue);
        document.addEventListener('visibilitychange', checkWhenDue);
        return { check };
    },
};

registry.category('services').add('employee_daily_logout', dailyLogoutService);
