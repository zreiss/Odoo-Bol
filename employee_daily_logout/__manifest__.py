{
    'name': 'Employee Daily Logout',
    'version': '19.0.1.0.0',
    'category': 'Administration',
    'summary': 'End employee sessions daily at 6:30 PM Eastern Time',
    'depends': ['web', 'auth_totp_mail'],
    'assets': {
        'web.assets_backend': [
            'employee_daily_logout/static/src/daily_logout_service.js',
        ],
        'web.assets_tests': [
            'employee_daily_logout/static/tests/tours/daily_logout.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
