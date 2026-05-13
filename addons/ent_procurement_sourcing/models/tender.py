from odoo import models, fields, api

class ProcurementTender(models.Model):
    _name = 'ent.tender'
    _description = 'Two-Envelope Tender Workspace'

    name = fields.Char(string='Tender Reference', required=True, copy=False, default='New')
    title = fields.Char(string='Tender Title', required=True)
    
    # Link back to the Demand phase
    ro_id = fields.Many2one('ent.request.order', string='Source Request Order', domain="[('state', '=', 'approved')]")
    
    # The State Machine for the Two-Envelope process
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published (Receiving Bids)'),
        ('tech_eval', 'Technical Evaluation (Env 1)'),
        ('comm_eval', 'Commercial Evaluation (Env 2)'),
        ('awarded', 'Awarded'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True)

    # Vendor Invitations (Applying strict VMS domain rules)
    vendor_ids = fields.Many2many(
        'res.partner', 
        string='Invited Vendors', 
        domain="[('is_pre_qualified', '=', True), ('blacklist_status', '=', 'active')]"
    )

    line_ids = fields.One2many('ent.tender.line', 'tender_id', string='Tender Lines')

    # NEW: Link to the Bids
    bid_ids = fields.One2many('ent.tender.bid', 'tender_id', string='Vendor Submissions')

    # NEW: Count the POs to display on the Smart Button
    po_count = fields.Integer(compute='_compute_po_count', string='Purchase Orders')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('ent.tender') or 'New'
        return super().create(vals_list)

    # Auto-pull data from the Request Order
    @api.onchange('ro_id')
    def _onchange_ro_id(self):
        if self.ro_id:
            self.title = self.ro_id.request_title
            
            # Clear existing lines to prevent duplicates if user changes the RO
            self.line_ids = [(5, 0, 0)]
            
            # Copy lines from RO to Tender
            new_lines = []
            for line in self.ro_id.line_ids:
                new_lines.append((0, 0, {
                    'name': line.name,
                    'quantity': line.quantity,
                    'uom_id': line.uom_id.id,
                }))
            self.line_ids = new_lines

    # NEW: State Machine Workflow (The Electronic Seal Logic)
    def action_publish(self):
        for rec in self:
            if not rec.vendor_ids:
                raise UserError("You must invite at least one pre-qualified vendor before publishing.")
            rec.state = 'published'

    def action_start_tech_eval(self):
        for rec in self:
            if not rec.bid_ids:
                raise UserError("Cannot start evaluation. No bids have been submitted yet.")
            rec.state = 'tech_eval'

    def action_open_commercial_envelope(self):
        for rec in self:
            # Audit Check: Ensure at least one vendor passed the technical round
            passed_bids = rec.bid_ids.filtered(lambda b: b.tech_status == 'passed')
            if not passed_bids:
                raise UserError("You cannot open Commercial Envelopes until at least one vendor has 'Passed' the Technical Evaluation.")
            rec.state = 'comm_eval'

    def _compute_po_count(self):
        for rec in self:
            rec.po_count = len(rec.bid_ids.filtered(lambda b: b.po_id))

    def action_view_pos(self):
        self.ensure_one()
        po_ids = self.bid_ids.mapped('po_id').ids
        return {
            'name': 'Purchase Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', po_ids)],
        }
class ProcurementTenderLine(models.Model):
    _name = 'ent.tender.line'
    _description = 'Tender Line Item'

    tender_id = fields.Many2one('ent.tender', string='Tender Reference', required=True, ondelete='cascade')
    name = fields.Char(string='Requested Item (Free Text)', required=True)
    
    # NEW: The Master Data Product Mapping
    product_id = fields.Many2one('product.product', string='Mapped Product')
    
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')

    # Automatically update UoM if they select a product
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_po_id or self.product_id.uom_id
    