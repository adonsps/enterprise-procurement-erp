from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # E-Procurement VMS Fields
    is_pre_qualified = fields.Boolean(
        string='Pre-Qualified Vendor', 
        default=False,
        help="Only pre-qualified vendors can be invited to Two-Envelope Tenders."
    )
    
    vendor_type = fields.Selection([
        ('local_indonesia', 'Local (Indonesia)'),
        ('international_import', 'International / Import'),
        ('sme_msme', 'SME / MSME')
    ], string='Vendor Classification', default='local_indonesia')
    
    blacklist_status = fields.Selection([
        ('active', 'Active & Cleared'),
        ('warning', 'Under Observation'),
        ('blacklisted', 'Blacklisted')
    ], string='Compliance Status', default='active', required=True)
    
    vpe_trust_score = fields.Float(
        string='VPE Trust Score (0-100)', 
        default=0.0,
        help="Vendor Performance Evaluation based on historical delivery and quality."
    )