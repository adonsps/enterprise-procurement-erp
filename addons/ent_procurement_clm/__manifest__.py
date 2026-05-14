{
    'name': 'Procurement Contract Lifecycle Management (CLM)',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Manage Long-Term Contracts, SLAs, and Expiration Alerts',
    'depends': ['ent_purchase_approval', 'ent_procurement_sourcing', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/cron_jobs.xml',
        'report/contract_report.xml',     # NEW: PDF Report Engine
        'views/contract_view.xml',
        'views/tender_bid_inherit_view.xml', # NEW: UI Bridge
    ],
    'installable': True,
    'application': True,
}