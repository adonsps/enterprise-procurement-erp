from odoo import models, fields

class ApprovalMatrix(models.Model):
    _name = 'ent.approval.matrix'
    _description = 'Purchase Approval Matrix'
    _order = 'sequence'

    name = fields.Char('Role / Tier Name', required=True)
    sequence = fields.Integer('Sequence', default=10, help="Order of approval (e.g., 10, 20, 30)")
    limit_amount = fields.Monetary('Maximum Approval Limit', currency_field='currency_id', help="Maximum amount this role can approve. Set to 0.0 for unlimited.")
    approver_id = fields.Many2one('res.users', string='Assigned Approver', required=True)
    
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')