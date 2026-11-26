{
    'name': 'EPA Refrigerant Account Records',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Private, reviewed EPA 608 certification files on customer accounts',
    'description': """
EPA account records — first implementation stage
================================================
Records Section 608 certification and employer evidence on the commercial
customer account. Reviewed versions are retained, private, and protected
against replacement or deletion. Company contacts share the account file.

This stage does NOT yet enforce refrigerant sales restrictions or produce
the retailer sales log. Do not use account status as a substitute for those
controls until the subsequent integration stages have been deployed.
    """,
    'depends': ['sales_team', 'web'],
    'data': [
        'security/epa_security.xml',
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ehs_epa_refrigerant/static/src/epa_account.js',
            'ehs_epa_refrigerant/static/src/epa_account.xml',
            'ehs_epa_refrigerant/static/src/epa_account.scss',
        ],
        'web.assets_tests': [
            'ehs_epa_refrigerant/static/tests/tours/epa_account.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
