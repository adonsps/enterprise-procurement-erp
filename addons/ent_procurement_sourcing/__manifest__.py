{
    'name': 'Procurement Sourcing (Two-Envelope)',
    'version': '1.0',
    'category': 'Purchases',
    'depends': ['ent_procurement_demand', 'ent_procurement_vendor', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/default_tender_matrix.xml',
        'report/comparison_report.xml',
        'views/tender_view.xml',
        'views/tender_approval_workflow_view.xml',
        'views/dashboard_views.xml', # NEW FILE
    ],
    'installable': True,
    'application': True,
}