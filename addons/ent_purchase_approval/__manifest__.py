{
    'name': 'Procurement Purchase Approval Matrix',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Dynamic Multi-Tier PO Approval Engine',
    'depends': ['ent_procurement_demand', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/default_matrix.xml',
        'views/approval_matrix_view.xml',
        'views/purchase_order_view.xml',
    ],
    'installable': True,
    'application': True,
}