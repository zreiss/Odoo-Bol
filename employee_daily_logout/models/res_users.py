import hashlib
import hmac
import time

from odoo import models
from odoo.http import request

from ..session_policy import cutoff_bounds


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _compute_session_token(self, sid):
        token = super()._compute_session_token(sid)
        if not token or not self._is_internal():
            return token
        # Keep core password/active-state invalidation. Only the employee
        # browser-session signature changes at each daily cutoff; API keys
        # are separate credentials and do not use this method.
        previous, _next = cutoff_bounds(time.time())
        if request:
            # A request admitted before cutoff must not mint a fresh signature
            # through automatic session rotation after cutoff.
            previous = getattr(request, '_employee_daily_logout_epoch', previous)
        return hmac.new(
            token.encode(), str(int(previous)).encode(), hashlib.sha256,
        ).hexdigest()

    def _legacy_session_token_hash_compute(self, sid):
        if self._is_internal():
            # The core legacy upgrade path must not revive a pre-cutoff token.
            return False
        return super()._legacy_session_token_hash_compute(sid)
