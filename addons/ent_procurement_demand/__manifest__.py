{
    'name': 'Procurement Demand & Planning',
    'version': '1.0',
    'category': 'Purchases',
    'depends': ['ent_procurement_core'], # It relies on your base!
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/request_order_view.xml'
    ],
    'installable': True,
}