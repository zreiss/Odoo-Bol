{
    'name': 'Bill of Lading Report',
    'version': '19.0.1.1.0',
    'category': 'Inventory/Inventory',
    'summary': 'Printable Bill of Lading for shipments',
    'description': """
Bill of Lading
==============
Adds a Bill of Lading PDF report to outgoing shipments (stock.picking),
printable from the Print menu of a single shipment or from the list view
for several shipments at once. The document shows shipper and consignee
addresses, carrier and tracking reference, total weight, package count,
the shipped products and signature blocks for shipper and carrier.
    """,
    'depends': ['stock_delivery'],
    'data': [
        'reports/bol_report.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'bol_report_stock/static/src/scss/bol_report.scss',
        ],
        'web.assets_tests': [
            'bol_report_stock/static/tests/tours/bol_print_menu.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
