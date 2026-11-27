from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from lxml import html

from odoo import http
from odoo.service.security import check_session
from odoo.tests import HttpCase, TransactionCase, get_db_name, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestEmployeeMfaPolicy(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = new_test_user(cls.env, 'daily_mfa_employee', groups='base.group_user')
        cls.portal = new_test_user(cls.env, 'daily_mfa_portal', groups='base.group_portal')

    def test_native_employee_only_policy(self):
        self.env['ir.config_parameter'].set_param('auth_totp.policy', 'employee_required')
        self.assertEqual(self.employee._mfa_type(), 'totp_mail')
        self.assertIsNone(self.portal._mfa_type())
        self.assertTrue(self.employee._rpc_api_keys_only())
        self.assertFalse(self.portal._rpc_api_keys_only())

    def test_employee_tokens_change_at_cutoff_not_portal(self):
        sid = 'daily-logout-test-session'
        before = datetime(2026, 11, 27, 23, 29, 59, tzinfo=timezone.utc).timestamp()
        with patch('odoo.addons.employee_daily_logout.models.res_users.time.time', return_value=before):
            employee_token = self.employee._compute_session_token(sid)
            portal_token = self.portal._compute_session_token(sid)
        with patch('odoo.addons.employee_daily_logout.models.res_users.time.time', return_value=before + 1):
            self.assertNotEqual(employee_token, self.employee._compute_session_token(sid))
            self.assertEqual(portal_token, self.portal._compute_session_token(sid))
            self.assertFalse(self.employee._legacy_session_token_hash_compute(sid))

    def test_session_validation_and_relogin(self):
        session = http.root.session_store.new()
        session.update(http.get_default_session(), uid=self.employee.id)
        self.addCleanup(http.root.session_store.delete, session)
        before = datetime(2026, 11, 27, 23, 29, 59, tzinfo=timezone.utc).timestamp()
        with patch('odoo.addons.employee_daily_logout.models.res_users.time.time', return_value=before):
            session.session_token = self.employee._compute_session_token(session.sid)
            self.assertTrue(check_session(session, self.env))
        with patch('odoo.addons.employee_daily_logout.models.res_users.time.time', return_value=before + 1):
            self.assertFalse(check_session(session, self.env))
            session.session_token = self.employee._compute_session_token(session.sid)
            self.assertTrue(check_session(session, self.env))

    def test_inflight_rotation_does_not_cross_daily_boundary(self):
        sid = 'inflight-daily-session'
        before = datetime(2026, 11, 27, 23, 29, 59, tzinfo=timezone.utc).timestamp()
        with patch('odoo.addons.employee_daily_logout.models.res_users.time.time', return_value=before):
            old_token = self.employee._compute_session_token(sid)
        epoch = before - (24 * 3600 - 1)
        with (
            patch('odoo.addons.employee_daily_logout.models.res_users.time.time', return_value=before + 2),
            patch('odoo.addons.employee_daily_logout.models.res_users.request',
                  SimpleNamespace(_employee_daily_logout_epoch=epoch)),
        ):
            self.assertEqual(old_token, self.employee._compute_session_token(sid))

    def test_password_and_active_state_still_invalidate_sessions(self):
        sid = 'daily-password-change-session'
        token = self.employee._compute_session_token(sid)
        self.employee.password = 'different-test-password'
        self.assertNotEqual(token, self.employee._compute_session_token(sid))
        token = self.employee._compute_session_token(sid)
        self.employee.active = False
        self.assertNotEqual(token, self.employee._compute_session_token(sid))

    def test_soft_rotation_before_cutoff_does_not_extend_access(self):
        session = http.root.session_store.new()
        session.update(http.get_default_session(), uid=self.employee.id)
        self.addCleanup(http.root.session_store.delete, session)
        before = datetime(2026, 11, 27, 23, 29, 59, tzinfo=timezone.utc).timestamp()
        with patch('odoo.addons.employee_daily_logout.models.res_users.time.time', return_value=before):
            session.session_token = self.employee._compute_session_token(session.sid)
            http.root.session_store.save(session)
            old_sid = session.sid
            self.addCleanup(http.root.session_store.delete, http.root.session_store.get(old_sid))
            http.root.session_store.rotate(session, self.env, soft=True)
            self.assertTrue(check_session(session, self.env))
        with patch('odoo.addons.employee_daily_logout.models.res_users.time.time', return_value=before + 2):
            self.assertFalse(check_session(session, self.env))

    def test_portal_legacy_tokens_remain_accepted(self):
        session = http.root.session_store.new()
        session.update(http.get_default_session(), uid=self.portal.id)
        self.addCleanup(http.root.session_store.delete, session)
        session.session_token = self.portal._legacy_session_token_hash_compute(session.sid)
        self.assertTrue(check_session(session, self.env))


@tagged('post_install', '-at_install')
class TestDailyLogoutHttp(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = new_test_user(cls.env, 'daily_http_employee', groups='base.group_user')
        cls.portal = new_test_user(cls.env, 'daily_http_portal', groups='base.group_portal')

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].set_param('auth_totp.policy', '')

    def session_info(self):
        return self.url_open('/web/session/get_session_info', json={'params': {}}).json()

    def expire_session(self, sid):
        session = http.root.session_store.get(sid)
        session.session_token = 'expired-daily-signature'
        http.root.session_store.save(session)

    def test_http_expiry_and_immediate_relogin(self):
        session = self.authenticate(self.employee.login, self.employee.login)
        result = self.session_info()['result']
        self.assertEqual(result['uid'], self.employee.id)
        policy = result['employee_daily_logout']
        self.assertGreater(policy['next_cutoff'], policy['server_now'])
        self.expire_session(session.sid)
        error = self.session_info()['error']
        self.assertEqual(error['data']['name'], 'odoo.http.SessionExpiredException')
        self.authenticate(self.employee.login, self.employee.login)
        self.assertEqual(self.session_info()['result']['uid'], self.employee.id)

    def test_portal_has_no_logout_timer(self):
        self.authenticate(self.portal.login, self.portal.login)
        result = self.session_info()['result']
        self.assertEqual(result['uid'], self.portal.id)
        self.assertNotIn('employee_daily_logout', result)

    def test_api_key_works_with_employee_mfa_required(self):
        self.env['ir.config_parameter'].set_param('auth_totp.policy', 'employee_required')
        key = self.env['res.users.apikeys'].with_user(self.employee)._generate(
            None, 'Daily logout integration test', datetime.now() + timedelta(days=1),
        )
        result = self.xmlrpc_object.execute_kw(
            get_db_name(), self.employee.id, key, 'res.users', 'read',
            [[self.employee.id], ['login']],
        )
        self.assertEqual(result[0]['login'], self.employee.login)

    def test_employee_two_step_signin_and_portal_exclusion(self):
        self.env['ir.config_parameter'].set_param('auth_totp.policy', 'employee_required')
        session = self.authenticate(self.employee.login, self.employee.login)
        # HttpCase's authentication helper finalizes sessions deliberately;
        # exercise the real password endpoint to assert partial MFA state.
        self.url_open('/web/session/logout')
        response = self.url_open('/web/session/authenticate', json={'params': {
            'db': get_db_name(), 'login': self.employee.login, 'password': self.employee.login,
        }}).json()
        self.assertIsNone(response['result']['uid'])
        token = self.employee._get_totp_mail_code()[0]
        # GET normally sends the code. Capture no real email in this isolated test.
        with patch.object(self.registry['res.users'], '_send_totp_mail_code', return_value=None):
            page = self.url_open('/web/login/totp')
        csrf = html.fromstring(page.content).xpath('//input[@name="csrf_token"]/@value')[0]
        response = self.url_open('/web/login/totp', data={
            'csrf_token': csrf, 'totp_token': token, 'redirect': '/odoo',
        }, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.session_info()['result']['uid'], self.employee.id)
        self.url_open('/web/session/logout')
        response = self.url_open('/web/session/authenticate', json={'params': {
            'db': get_db_name(), 'login': self.portal.login, 'password': self.portal.login,
        }}).json()
        self.assertEqual(response['result']['uid'], self.portal.id)

    def test_expired_session_tour(self):
        # Install a route only in the test process; no expiry endpoint is
        # registered by the installed addon in a normal Odoo server.
        class TestExpiryController(http.Controller):
            @http.route('/employee-daily-logout-test/expire', type='jsonrpc', auth='user')
            def expire(self):
                http.request.session.session_token = 'expired-daily-signature'
                return True

        self.registry.clear_cache('routing')
        ir_http = self.registry['ir.http']
        original_session_info = ir_http.session_info

        def fast_timer(model):
            info = original_session_info(model)
            if info.get('employee_daily_logout'):
                info['employee_daily_logout']['next_cutoff'] = info['employee_daily_logout']['server_now'] + 2
            return info

        with patch.object(ir_http, 'session_info', fast_timer):
            self.start_tour('/odoo', 'employee_daily_logout', login=self.employee.login)
