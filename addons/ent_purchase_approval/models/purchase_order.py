from odoo import models, fields, api
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approval_line_ids = fields.One2many('ent.po.approval.line', 'po_id', string='Approval Workflow')
    current_approver_id = fields.Many2one('res.users', string='Pending Approver', readonly=True, copy=False)

    def button_draft(self):
        # Clear old approvals when the PO is reset to draft
        res = super(PurchaseOrder, self).button_draft()
        for order in self:
            order.approval_line_ids.unlink()
            order.current_approver_id = False
        return res

    def button_confirm(self):
        for order in self:
            if order.state in ['purchase', 'done']:
                return super(PurchaseOrder, order).button_confirm()

            # If approval lines exist, check if they are all approved
            if order.approval_line_ids:
                pending = order.approval_line_ids.filtered(lambda l: l.status == 'pending')
                if not pending:
                    # All approved, proceed to officially confirm the contract
                    return super(PurchaseOrder, order).button_confirm()
                else:
                    # Still pending approvals, stop here
                    return True

            # Otherwise, generate the dynamic matrix based on the current amount_total
            matrix_records = self.env['ent.approval.matrix'].search([], order='sequence asc')
            if not matrix_records:
                return super(PurchaseOrder, order).button_confirm()

            required_approvals = []
            for matrix in matrix_records:
                required_approvals.append((0, 0, {
                    'matrix_id': matrix.id,
                    'approver_id': matrix.approver_id.id,
                    'status': 'pending'
                }))
                # Stop adding tiers if this tier's limit is large enough to cover the PO total
                if matrix.limit_amount > 0.0 and order.amount_total <= matrix.limit_amount:
                    break 
            
            if required_approvals:
                order.write({
                    'approval_line_ids': required_approvals,
                    'state': 'to approve',
                    'current_approver_id': required_approvals[0][2]['approver_id']
                })
            else:
                return super(PurchaseOrder, order).button_confirm()
        return True

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        # Security Governance: Intercept saves. If the line items are modified while pending, recalculate!
        if 'order_line' in vals:
            for order in self.filtered(lambda o: o.state == 'to approve'):
                # Delete the outdated matrix and force the engine to rebuild it
                order.approval_line_ids.unlink()
                order.button_confirm()
        return res

    def action_approve_po_custom(self):
        for order in self:
            if self.env.user != order.current_approver_id and not self.env.is_admin():
                raise UserError(f"Security Block: Only {order.current_approver_id.name} is authorized to approve this document at this stage.")
            
            # Mark current step as Approved
            pending_line = order.approval_line_ids.filtered(lambda l: l.status == 'pending')
            if pending_line:
                pending_line[0].write({
                    'status': 'approved',
                    'date_approved': fields.Datetime.now()
                })
            
            # Move to the next approver, or finish the PO if done
            next_line = order.approval_line_ids.filtered(lambda l: l.status == 'pending')
            if next_line:
                order.current_approver_id = next_line[0].approver_id.id
            else:
                order.current_approver_id = False
                # Re-trigger confirmation. It will see all lines are approved and finalize the PO.
                order.button_confirm()

    def action_reject_po_custom(self):
        for order in self:
            if self.env.user != order.current_approver_id and not self.env.is_admin():
                raise UserError("Security Block: You are not authorized to reject this document.")
            
            pending_line = order.approval_line_ids.filtered(lambda l: l.status == 'pending')
            if pending_line:
                pending_line[0].write({'status': 'rejected'})
            
            order.write({
                'state': 'cancel',
                'current_approver_id': False
            })

class POApprovalLine(models.Model):
    _name = 'ent.po.approval.line'
    _description = 'PO Approval Line'

    po_id = fields.Many2one('purchase.order', ondelete='cascade')
    matrix_id = fields.Many2one('ent.approval.matrix', string='Approval Tier')
    approver_id = fields.Many2one('res.users', string='Approver')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='pending')
    date_approved = fields.Datetime('Date Approved')