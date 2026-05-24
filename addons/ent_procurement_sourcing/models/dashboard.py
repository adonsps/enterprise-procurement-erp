from odoo import models, fields, api

class ProcurementWorklist(models.Model):
    _name = 'ent.procurement.worklist'
    _description = 'Procurement Worklist Dashboard'

    name = fields.Char(default='Daily Action Items')
    color = fields.Integer(default=3)

    # Real-time computed metrics
    pending_ro_count = fields.Integer(compute='_compute_counts')
    active_tender_count = fields.Integer(compute='_compute_counts')
    pending_approval_count = fields.Integer(compute='_compute_counts')

    def _compute_counts(self):
        for rec in self:
            # 1. Unprocessed Request Orders
            rec.pending_ro_count = self.env['ent.request.order'].search_count([('state', 'not in', ['done', 'cancel'])])
            
            # 2. Ongoing Tenders in Evaluation
            rec.active_tender_count = self.env['ent.tender'].search_count([('state', 'in', ['draft', 'published', 'tech_eval', 'comm_eval'])])
            
            # 3. Approvals Bottlenecks
            rec.pending_approval_count = self.env['ent.tender'].search_count([('state', '=', 'waiting_approval')])

    # Call-To-Action (CTA) Routing Functions
    def action_open_ro(self):
        return {
            'name': 'Action Needed: Request Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'ent.request.order',
            'view_mode': 'tree,form',
            'domain': [('state', 'not in', ['done', 'cancel'])],
        }

    def action_open_tenders(self):
        return {
            'name': 'Action Needed: Ongoing Tenders',
            'type': 'ir.actions.act_window',
            'res_model': 'ent.tender',
            'view_mode': 'tree,form',
            'domain': [('state', 'in', ['draft', 'published', 'tech_eval', 'comm_eval'])],
        }

    def action_open_approvals(self):
        return {
            'name': 'Action Needed: Pending Approvals',
            'type': 'ir.actions.act_window',
            'res_model': 'ent.tender',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'waiting_approval')],
        }