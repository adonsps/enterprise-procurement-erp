from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

class TenderBid(models.Model):
    _name = 'ent.tender.bid'
    _description = 'Tender Bid Submission'

    # FIX 3: Strict Database Lock against duplicate vendors
    _sql_constraints = [
        ('unique_vendor_tender', 'UNIQUE(tender_id, vendor_id)', 
         'Audit Block: A vendor can only have ONE submission per Tender!')
    ]

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
    
    # Envelope 2: Commercial (Now calculated from the line items)
    currency_id = fields.Many2one(related='tender_id.ro_id.currency_id', string='Currency')
    bid_line_ids = fields.One2many('ent.tender.bid.line', 'bid_id', string='Commercial Pricing Breakdown')
    commercial_price = fields.Monetary(string='Envelope 2 (Total)', compute='_compute_commercial_price', store=True, currency_field='currency_id')

    po_id = fields.Many2one('purchase.order', string='Generated PO', readonly=True)
    # FIX: Keys must be strings ('1' instead of 1)
    award_rank = fields.Selection([
        ('1', 'Rank 1'),
        ('2', 'Rank 2'),
        ('3', 'Rank 3'),
        ('4', 'Rank 4'),
        ('5', 'Rank 5'),
        ('6', 'Rank 6'),
        ('7', 'Rank 7'),
        ('8', 'Rank 8'),
        ('9', 'Rank 9'),
        ('10', 'Rank 10')
    ], string='Vendor Rank (Allocation)', default='1', tracking=True)

    @api.constrains('tender_id', 'vendor_id')
    def _check_duplicate_vendor_submission(self):
        for bid in self:
            if bid.tender_id and bid.vendor_id:
                # Search the database for any other bid in this tender with the exact same vendor
                duplicate_count = self.env['ent.tender.bid'].search_count([
                    ('tender_id', '=', bid.tender_id.id),
                    ('vendor_id', '=', bid.vendor_id.id),
                    ('id', '!=', bid.id) # Exclude the current line being checked
                ])
                
                if duplicate_count > 0:
                    raise ValidationError(f"Audit Block: '{bid.vendor_id.name}' already has a submission! Each vendor is strictly limited to one submission per Tender.")

    @api.depends('bid_line_ids.subtotal')
    def _compute_commercial_price(self):
        for rec in self:
            rec.commercial_price = sum(line.subtotal for line in rec.bid_line_ids)

    # Automatically generate the Bid Lines based on the Tender's requested items
    @api.model_create_multi
    def create(self, vals_list):
        bids = super().create(vals_list)
        for bid in bids:
            if not bid.bid_line_ids and bid.tender_id:
                lines = []
                for t_line in bid.tender_id.line_ids:
                    lines.append((0, 0, {
                        'bid_id': bid.id,
                        'tender_line_id': t_line.id,
                    }))
                bid.write({'bid_line_ids': lines})
        return bids

    def action_award_bid(self):
        for bid in self:
            if bid.tender_id.state != 'comm_eval':
                raise UserError("You can only award a bid during the Commercial Evaluation phase.")
            if bid.tech_status != 'passed':
                raise UserError("You cannot award a disqualified vendor.")
            # 1. ALWAYS generate the CLM Document (This acts as your PPH for Outline Agreements)
            if hasattr(bid, '_execute_contract_generation'):
                bid._execute_contract_generation()
            # Strict Product Mapping Audit
            unmapped_lines = bid.tender_id.line_ids.filtered(lambda l: not l.product_id)
            if unmapped_lines:
                raise UserError("Audit Failed: The Procurement PIC must map all Requested Items to a valid Master Data Product in the 'Requested Items' tab before awarding.")

            
            # 2. FIX: ONLY create a Purchase Order if the Tender is Transactional
            if bid.tender_id.tender_purpose == 'transactional':
                # Draft the Purchase Order automatically
                po_vals = {
                    'partner_id': bid.vendor_id.id,
                    'origin': bid.tender_id.name, 
                    'order_line': [],
                }
                # Map the tender line items into the PO using the specific Bid Line unit prices
                for line in bid.tender_id.line_ids:
                    # Find the corresponding pricing line submitted by this vendor
                    bid_line = bid.bid_line_ids.filtered(lambda b: b.tender_line_id == line)
                    actual_unit_price = bid_line.price_unit if bid_line else 0.0

                    po_vals['order_line'].append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.name, 
                        'product_qty': line.quantity,
                        'product_uom': line.uom_id.id,
                        'price_unit': actual_unit_price, 
                        'date_planned': fields.Datetime.now(),
                    }))
                    
                # Create the PO
                new_po = self.env['purchase.order'].create(po_vals)
                new_po.button_confirm() 
                
                # Link it and close the tender
                bid.po_id = new_po.id
                bid.tender_id.state = 'awarded'

# --- NEW: The Bid Line Table ---
class TenderBidLine(models.Model):
    _name = 'ent.tender.bid.line'
    _description = 'Tender Bid Line Item'

    bid_id = fields.Many2one('ent.tender.bid', string='Bid Reference', required=True, ondelete='cascade')
    tender_line_id = fields.Many2one('ent.tender.line', string='Tender Line', required=True)
    
    # Context pulled from the original Tender Line
    name = fields.Char(related='tender_line_id.name', string='Description', readonly=True)
    quantity = fields.Float(related='tender_line_id.quantity', string='Quantity', readonly=True)
    uom_id = fields.Many2one(related='tender_line_id.uom_id', string='UoM', readonly=True)
    
    # Financials
    currency_id = fields.Many2one(related='bid_id.currency_id')
    price_unit = fields.Monetary(string='Unit Price', currency_field='currency_id')
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', store=True, currency_field='currency_id')

    award_rank = fields.Integer(string='Vendor Rank (Allocation)', default=1, tracking=True)

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit