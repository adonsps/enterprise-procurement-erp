{
    'name': 'Procurement Sourcing (Two-Envelope)',
    'version': '1.0',
    'category': 'Purchases',
    'depends': ['ent_procurement_demand', 'ent_procurement_vendor'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/tender_view.xml',
    ],
    'installable': True,
    'application': True,
}