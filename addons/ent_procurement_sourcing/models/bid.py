from odoo import models, fields, api
from odoo.exceptions import UserError

class TenderBid(models.Model):
    _name = 'ent.tender.bid'
    _description = 'Tender Bid Submission'

    tender_id = fields.Many2one('ent.tender', string='Tender', required=True, ondelete='cascade')
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True)
    
    # Envelope 1: Technical
    tech_proposal_filename = fields.Char(string='Tech Proposal Filename')
    tech_proposal = fields.Binary(string='Envelope 1 (Technical)', attachment=True)
    tech_status = fields.Selection([
        ('pending', 'Pending Evaluation'),
        ('passed', 'Passed Technical'),
        ('failed', 'Disqualified')
    ], string='Technical Result', default='pending', required=True)
    
    # Envelope 2: Commercial
    currency_id = fields.Many2one(related='tender_id.ro_id.currency_id', string='Currency')
    commercial_price = fields.Monetary(string='Envelope 2 (Commercial Total)', currency_field='currency_id')