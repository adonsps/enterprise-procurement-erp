from odoo import models, fields, api
from datetime import timedelta

class ProcurementContract(models.Model):
    _name = 'ent.contract'
    _description = 'Procurement Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin'] # Enables the Chatter and Activities

    name = fields.Char(string='Contract Reference', required=True, copy=False, default='New', tracking=True)
    title = fields.Char(string='Contract Title', required=True, tracking=True)
    
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True, tracking=True)
    po_id = fields.Many2one('purchase.order', string='Source Purchase Order')
    pic_id = fields.Many2one('res.users', string='Procurement PIC', default=lambda self: self.env.user, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft / Under Negotiation'),
        ('active', 'Active'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated')
    ], string='Status', default='draft', tracking=True)

    # NEW: Contract Template Type
    contract_type = fields.Selection([
        ('outline', 'Outline Agreement (Internal Catalogue & Price Lock)'),
        ('pks', 'Perjanjian Kerja Sama / PKS (Basic Procurement Commitment)'),
        ('pjk', 'Perjanjian Jasa Konstruksi / PJK (Construction Services)')
    ], string='Contract Category', tracking=True)

    # Core Dates
    start_date = fields.Date(string='Effective Start Date', required=True, tracking=True)
    end_date = fields.Date(string='Expiration Date', required=True, tracking=True)
    notice_period_days = fields.Integer(string='Renewal Notice Period (Days)', default=60, help="How many days before expiration should the PIC be alerted?")
    
    # Financials
    currency_id = fields.Many2one(related='po_id.currency_id', store=True)
    contract_value = fields.Monetary(string='Total Contract Value', currency_field='currency_id', tracking=True)
    
    milestone_ids = fields.One2many('ent.contract.milestone', 'contract_id', string='Deliverables / Milestones')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('ent.contract') or 'New'
        return super().create(vals_list)

    def action_activate(self):
        self.state = 'active'

    def action_terminate(self):
        self.state = 'terminated'

    # --- The Automated Background Engine ---
    @api.model
    def _cron_check_expiring_contracts(self):
        today = fields.Date.today()
        # Find active contracts that need to be flagged
        active_contracts = self.search([('state', '=', 'active')])
        
        for contract in active_contracts:
            if contract.end_date:
                notice_date = contract.end_date - timedelta(days=contract.notice_period_days)
                
                # If today is past the end date, it's expired
                if today > contract.end_date:
                    contract.state = 'expired'
                    contract.message_post(body="⚠️ System Alert: This contract has officially expired.")
                
                # If today is within the notice window, flag it and schedule an activity!
                elif today >= notice_date:
                    contract.state = 'expiring'
                    contract.message_post(body=f"🔔 System Alert: This contract is expiring in less than {contract.notice_period_days} days. Please begin renewal or retendering evaluation.")
                    
                    # Create a To-Do activity for the PIC
                    self.env['mail.activity'].create({
                        'res_id': contract.id,
                        'res_model_id': self.env['ir.model']._get('ent.contract').id,
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'summary': 'Evaluate Contract Renewal / Retender',
                        'user_id': contract.pic_id.id,
                        'date_deadline': contract.end_date,
                    })

class ContractMilestone(models.Model):
    _name = 'ent.contract.milestone'
    _description = 'Contract Milestone'

    contract_id = fields.Many2one('ent.contract', string='Contract', ondelete='cascade')
    name = fields.Char(string='Deliverable / SLA Description', required=True)
    expected_date = fields.Date(string='Target Date')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed / Breached')
    ], string='Status', default='pending')