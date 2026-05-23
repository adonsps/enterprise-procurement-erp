from odoo import models, fields, api
from odoo.exceptions import UserError

class VendorPerformanceEvaluation(models.Model):
    _name = 'ent.vendor.evaluation'
    _description = 'Vendor Performance Evaluation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Evaluation Reference', required=True, copy=False, readonly=True, default='New')
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True, readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Warehouse Receipt', required=True, readonly=True)
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order', related='picking_id.purchase_id', store=True)
    evaluator_id = fields.Many2one('res.users', string='Evaluator (PIC)', default=lambda self: self.env.user, required=True)
    evaluation_date = fields.Date('Date', default=fields.Date.context_today, required=True)

    # FIX: Removed required=True from Python level so background drafts can be created empty
    score_delivery = fields.Selection([('1','1 - Very Late'),('2','2 - Late'),('3','3 - On Time'),('4','4 - Early'),('5','5 - Exceptional')], string="Delivery Timeliness", tracking=True)
    score_quality = fields.Selection([('1','1 - Poor'),('2','2 - Below Specs'),('3','3 - Meets Specs'),('4','4 - High Quality'),('5','5 - Defect Free')], string="Product Quality", tracking=True)
    score_service = fields.Selection([('1','1 - Unresponsive'),('2','2 - Slow'),('3','3 - Acceptable'),('4','4 - Proactive'),('5','5 - Excellent')], string="Communication & Service", tracking=True)
    
    total_score = fields.Float('Overall Score (Out of 5)', compute='_compute_total_score', store=True)
    notes = fields.Text('Additional Feedback')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted')
    ], string='Status', default='draft', tracking=True)

    @api.depends('score_delivery', 'score_quality', 'score_service')
    def _compute_total_score(self):
        for record in self:
            if record.score_delivery and record.score_quality and record.score_service:
                total = (int(record.score_delivery) + int(record.score_quality) + int(record.score_service)) / 3.0
                record.total_score = round(total, 2)
            else:
                record.total_score = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('ent.vendor.evaluation') or 'EVAL/' + str(fields.Date.today())
        return super().create(vals_list)

    def action_submit_evaluation(self):
        for record in self:
            # FIX: Enforce the mandatory check here when the user tries to submit the scorecard
            if not record.score_delivery or not record.score_quality or not record.score_service:
                raise UserError("Validation Error: Please fill in all performance metrics (Delivery, Quality, and Service) before submitting the scorecard.")
            record.state = 'submitted'