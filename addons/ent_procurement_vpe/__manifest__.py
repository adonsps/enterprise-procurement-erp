{
    'name': 'Enterprise Vendor Performance Evaluation',
    'version': '1.0',
    'summary': 'Intercept warehouse receipts to enforce vendor performance scoring',
    'category': 'Inventory/Purchasing',
    'author': 'Enterprise Procurement',
    'depends': ['base', 'purchase', 'stock', 'ent_procurement_sourcing'],
    'data': [
        'security/ir.model.access.csv',
        'views/evaluation_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}