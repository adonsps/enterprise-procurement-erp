from odoo import models, fields, api
from odoo.exceptions import UserError

class TenderApprovalMatrix(models.Model):
    _name = 'ent.tender.approval.matrix'
    _description = 'Tender Approval Matrix'
    _order = 'sequence'

    name = fields.Char('Role / Tier Name', required=True)
    sequence = fields.Integer('Sequence', default=10)
    limit_amount = fields.Monetary('Maximum Approval Limit', currency_field='currency_id')
    approver_id = fields.Many2one('res.users', string='Assigned Approver', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

class TenderApprovalLine(models.Model):
    _name = 'ent.tender.approval.line'
    _description = 'Tender Approval Line'

    tender_id = fields.Many2one('ent.tender', ondelete='cascade')
    matrix_id = fields.Many2one('ent.tender.approval.matrix', string='Approval Tier')
    approver_id = fields.Many2one('res.users', string='Approver')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='pending')
    date_approved = fields.Datetime('Date Approved')

class ProcurementTenderInherit(models.Model):
    _inherit = 'ent.tender'

    tender_purpose = fields.Selection([
        ('transactional', 'Transactional (Spot Purchase / PO)'),
        ('outline', 'Price Locking (Outline Agreement)')
    ], string='Tender Purpose', tracking=True)

    state = fields.Selection(selection_add=[
        ('to_approve', 'Pending Approval')
    ], ondelete={'to_approve': 'set default'})

    proposed_bid_id = fields.Many2one('ent.tender.bid', string='Proposed Bid', readonly=True, copy=False)
    
    # NEW: Pull the clean Vendor Name for the UI
    proposed_vendor_id = fields.Many2one('res.partner', related='proposed_bid_id.vendor_id', string='Proposed Winner')

    approval_line_ids = fields.One2many('ent.tender.approval.line', 'tender_id', string='Approval Workflow')
    current_approver_id = fields.Many2one('res.users', string='Pending Approver', readonly=True, copy=False)

    def action_approve_tender(self):
        for tender in self:
            if self.env.user != tender.current_approver_id and not self.env.is_admin():
                raise UserError(f"Security Block: Only {tender.current_approver_id.name} is authorized to approve this Tender.")
            
            pending = tender.approval_line_ids.filtered(lambda l: l.status == 'pending')
            if pending:
                pending[0].write({'status': 'approved', 'date_approved': fields.Datetime.now()})
            
            next_line = tender.approval_line_ids.filtered(lambda l: l.status == 'pending')
            if next_line:
                tender.current_approver_id = next_line[0].approver_id.id
            else:
                tender.current_approver_id = False
                
                # NEW: Final approval reached! Mark the vendor as the official winner.
                if tender.proposed_bid_id:
                    tender.proposed_bid_id.is_awarded = True
                
                # Temporarily revert state so the original Award function runs smoothly
                tender.state = 'comm_eval'
                tender.proposed_bid_id.action_award_bid()

    def action_reject_tender(self):
        for tender in self:
            if self.env.user != tender.current_approver_id and not self.env.is_admin():
                raise UserError("Not authorized to reject.")
            
            pending = tender.approval_line_ids.filtered(lambda l: l.status == 'pending')
            if pending:
                pending[0].write({'status': 'rejected'})
            
            # Send back to commercial evaluation and clear the proposed winner so PIC can choose someone else
            tender.write({
                'state': 'comm_eval', 
                'current_approver_id': False, 
                'proposed_bid_id': False
            })
            tender.approval_line_ids.unlink()

class TenderBidInherit(models.Model):
    _inherit = 'ent.tender.bid'

    # NEW: Flag to indicate this vendor won
    is_awarded = fields.Boolean(string='Awarded Winner', default=False)

    def action_propose_award(self):
        # This replaces the immediate PO/Contract generation with the routing workflow
        for bid in self:
            if not bid.tender_id.tender_purpose:
                raise UserError("Please define the 'Tender Purpose' (Transactional or Outline Agreement) on the main Tender form before requesting approval.")
            
            matrix_records = self.env['ent.tender.approval.matrix'].search([], order='sequence asc')
            if not matrix_records:
                # If admin hasn't set up rules yet, auto-approve
                bid.tender_id.state = 'comm_eval'
                bid.action_award_bid()
                return

            required_approvals = []
            for matrix in matrix_records:
                required_approvals.append((0, 0, {
                    'matrix_id': matrix.id,
                    'approver_id': matrix.approver_id.id,
                    'status': 'pending'
                }))
                if matrix.limit_amount > 0.0 and bid.commercial_price <= matrix.limit_amount:
                    break 
            
            bid.tender_id.write({
                'proposed_bid_id': bid.id,
                'approval_line_ids': required_approvals,
                'state': 'to_approve',
                'current_approver_id': required_approvals[0][2]['approver_id']
            })