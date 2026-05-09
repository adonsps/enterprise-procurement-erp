from odoo import models, fields, apia

class RequestOrder(models.Model):
    _name = 'ent.request.order'
    _description = 'Procurement Request Order'

    # Core Information
    name = fields.Char(string='RO Number', required=True, copy=False, default='New')
    request_title = fields.Char(string='Request Title', required=True)
    department = fields.Char(string='Department')
    requestor_id = fields.Many2one('res.users', string='Requestor', default=lambda self: self.env.user)
    
    # Financials & Docs
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    estimated_budget = fields.Monetary(string='Estimated Budget', currency_field='currency_id')
    
    description = fields.Text(string='Business Justification')
    
    # The TOR File Upload
    tor_filename = fields.Char(string='TOR Filename')
    tor_attachment = fields.Binary(string='Terms of Reference (TOR)', attachment=True)
    
    # State Management (The "Hard Gates")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                # Fetch the next sequence number based on the code we set in XML
                vals['name'] = self.env['ir.sequence'].next_by_code('ent.request.order') or 'New'
        return super().create(vals_list)
    # --------------------------

    # Button Actions
    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'
            
    def action_approve(self):
        for rec in self:
            rec.state = 'approved'

