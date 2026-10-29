{
    'name': 'Product Catalog Attribute Filters',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Filter the product catalog by relevant product specifications',
    'depends': ['sale'],
    'data': [
        'views/product_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_catalog_attributes/static/src/catalog_attributes.js',
            'product_catalog_attributes/static/src/catalog_attributes.xml',
        ],
        'web.assets_tests': [
            'product_catalog_attributes/static/tests/tours/catalog_attributes.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
