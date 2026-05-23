{
    'name': 'Enterprise Procurement Catalog (Guided Buying)',
    'version': '1.0',
    'summary': 'Internal storefront for Outline Agreement (PPH) items to streamline Request Orders',
    'category': 'Purchasing',
    'author': 'Enterprise Procurement',
    'depends': ['base', 'ent_procurement_demand', 'ent_procurement_clm', 'ent_procurement_sourcing'],
    'data': [
        'security/ir.model.access.csv',
        'views/catalog_views.xml',
    ],
    'installable': True,
    'application': True,
}