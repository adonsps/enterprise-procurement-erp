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

    # Keep legacy fields invisible to prevent database crashes during upgrade
    proposed_bid_id = fields.Many2one('ent.tender.bid', string='Legacy Proposed Bid', copy=False)
    proposed_vendor_id = fields.Many2one('res.partner', related='proposed_bid_id.vendor_id', string='Legacy Proposed Winner')

    approval_line_ids = fields.One2many('ent.tender.approval.line', 'tender_id', string='Approval Workflow')
    current_approver_id = fields.Many2one('res.users', string='Pending Approver', readonly=True, copy=False)

    def action_submit_for_approval(self):
        for tender in self:
            if not tender.tender_purpose:
                raise UserError("Validation Error: Please define the 'Tender Purpose' (Transactional or Outline Agreement) before requesting approval.")
            
            proposed_bids = tender.bid_ids.filtered(lambda b: b.is_proposed)
            if not proposed_bids:
                raise UserError("Validation Error: You must select at least one winning vendor using the 'Select Winner' button before submitting for approval.")
            
            # Guardrail: Transactional POs usually only go to one vendor. Outline Agreements can be split.
            if tender.tender_purpose == 'transactional' and len(proposed_bids) > 1:
                raise UserError("Validation Error: Transactional (PO) Tenders only support ONE winning vendor in this version. To split POs, please process them as separate Outline Agreements.")

            
           # --- RANKING VALIDATION ENGINE ---
            if tender.tender_purpose == 'outline' and tender.allocation_strategy == 'ranked':
                # FIX: Convert the string selection back to an integer for the math check
                ranks = [int(b.award_rank) for b in proposed_bids if b.award_rank]
                
                # Check 1: No duplicates allowed
                if len(set(ranks)) != len(ranks):
                    raise UserError("Validation Error: Two or more proposed vendors have the same Award Rank. Each winner must have a unique rank (1, 2, 3...).")
                
                # Check 2: Must be perfectly sequential up to the total number of winners
                expected_ranks = set(range(1, len(proposed_bids) + 1))
                if set(ranks) != expected_ranks:
                    raise UserError(f"Validation Error: Ranks must be perfectly sequential starting from 1 up to the total number of winners ({len(proposed_bids)}). Please adjust the dropdowns.")
            
            # --- SMART CONTRACT ASSIGNMENT ---
            # Automatically assign the Outline Agreement contract template if applicable, 
            # bypassing the need for manual data entry per vendor.
            if tender.tender_purpose == 'outline':
                for bid in proposed_bids:
                    # Safely check if the CLM module is installed and linked
                    if hasattr(bid, 'contract_type'):
                        bid.contract_type = 'outline'

            # Calculate total valuation of ALL proposed winners to hit the correct matrix tier
            total_valuation = sum(proposed_bids.mapped('commercial_price'))
            
            matrix_records = self.env['ent.tender.approval.matrix'].search([], order='sequence asc')
            if not matrix_records:
                tender.state = 'comm_eval'
                for bid in proposed_bids:
                    bid.is_awarded = True
                    bid.action_award_bid()
                return

            required_approvals = []
            for matrix in matrix_records:
                required_approvals.append((0, 0, {
                    'matrix_id': matrix.id,
                    'approver_id': matrix.approver_id.id,
                    'status': 'pending'
                }))
                # Matrix checks the COMBINED value of all selected Outline Agreements
                if matrix.limit_amount > 0.0 and total_valuation <= matrix.limit_amount:
                    break 
            
            tender.write({
                'approval_line_ids': required_approvals,
                'state': 'to_approve',
                'current_approver_id': required_approvals[0][2]['approver_id']
            })

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
                
                proposed_bids = tender.bid_ids.filtered(lambda b: b.is_proposed)
                for bid in proposed_bids:
                    bid.is_awarded = True
                
                # Automatically generate contracts for ALL approved winners sequentially
                for bid in proposed_bids:
                    # FIX: Force the state back to comm_eval before EACH vendor is processed
                    # so they bypass the security block individually.
                    tender.state = 'comm_eval'
                    bid.action_award_bid()
                
                # Once every vendor has their contract/PO, permanently lock the Tender
                tender.state = 'awarded'

    def action_reject_tender(self):
        for tender in self:
            if self.env.user != tender.current_approver_id and not self.env.is_admin():
                raise UserError("Not authorized to reject.")
            
            pending = tender.approval_line_ids.filtered(lambda l: l.status == 'pending')
            if pending:
                pending[0].write({'status': 'rejected'})
            
            # Un-flag all proposed winners so the buyer can choose new ones
            for bid in tender.bid_ids:
                bid.is_proposed = False

            tender.write({
                'state': 'comm_eval', 
                'current_approver_id': False, 
            })
            tender.approval_line_ids.unlink()

class TenderBidInherit(models.Model):
    _inherit = 'ent.tender.bid'

    is_awarded = fields.Boolean(string='Awarded Winner', default=False)
    # NEW: Flag to hold the vendor in the "Cart" before submission
    is_proposed = fields.Boolean(string='Proposed', default=False)

    def action_toggle_propose(self):
        for bid in self:
            bid.is_proposed = not bid.is_proposed