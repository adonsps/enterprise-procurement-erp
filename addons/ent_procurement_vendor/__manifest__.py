{
    'name': 'Procurement Vendor Management (VMS)',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Vendor Pre-qualification, Trust Scores, and Master Data',
    'depends': ['ent_procurement_core', 'contacts'],
    'data': [
        'views/res_partner_view.xml',
        'data/vendor_data.xml',
    ],
    'installable': True,
    'application': True,
}