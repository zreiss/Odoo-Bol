import time

from odoo import models
from odoo.http import request

from ..session_policy import cutoff_bounds


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _authenticate_explicit(cls, auth):
        if request.session.uid:
            request._employee_daily_logout_epoch = cutoff_bounds(time.time())[0]
        return super()._authenticate_explicit(auth)

    def session_info(self):
        info = super().session_info()
        if request.session.uid and self.env.user._is_internal():
            now = time.time()
            _previous, following = cutoff_bounds(now)
            info['employee_daily_logout'] = {
                'server_now': now,
                'next_cutoff': following,
            }
        return info
