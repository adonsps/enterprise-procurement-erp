{
    'name': 'Procurement Demand & Planning',
    'version': '1.0',
    'category': 'Purchases',
    'depends': ['ent_procurement_core', 'product'], # Added 'product' here!
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/product_category_view.xml',          # We will create this next
        'views/request_order_view.xml',
    ],
    'installable': True,
}