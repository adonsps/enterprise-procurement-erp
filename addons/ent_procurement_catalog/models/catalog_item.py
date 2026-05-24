from odoo import models, fields, api
from odoo.exceptions import UserError
import random

class ProcurementCatalogItem(models.Model):
    _name = 'ent.catalog.item'
    _description = 'Catalog Product Master'
    _order = 'name asc'

    product_id = fields.Many2one('product.product', string='Product / Material', required=True)
    name = fields.Char(related='product_id.name', string='Item Name', store=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    active = fields.Boolean('Active', default=True)

    # Hidden Vendor Pool
    vendor_line_ids = fields.One2many('ent.catalog.vendor.line', 'catalog_item_id', string='Vendor Contracts')
    
    # Lowest price to show the requestor
    display_price = fields.Monetary(string='Starting Price', compute='_compute_display_price', currency_field='currency_id')

    @api.depends('vendor_line_ids.price_unit')
    def _compute_display_price(self):
        for item in self:
            prices = item.vendor_line_ids.mapped('price_unit')
            item.display_price = min(prices) if prices else 0.0

    def action_create_ro_from_catalog(self):
        return {
            'name': 'Specify Quantity',
            'type': 'ir.actions.act_window',
            'res_model': 'ent.catalog.order.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_catalog_item_id': self.id}
        }

class ProcurementCatalogVendorLine(models.Model):
    _name = 'ent.catalog.vendor.line'
    _description = 'Hidden Vendor Allocation Line'
    _order = 'award_rank asc, id asc'

    catalog_item_id = fields.Many2one('ent.catalog.item', required=True, ondelete='cascade')
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True)
    contract_id = fields.Many2one('ent.contract', string='Outline Agreement (PPH)', required=True)
    price_unit = fields.Float('Locked Price', required=True)
    
    allocation_strategy = fields.Selection([('equal', 'Equal'), ('ranked', 'Ranked')], string='Strategy')
    award_rank = fields.Integer('Rank', default=1)

class ProcurementCatalogWizard(models.TransientModel):
    _name = 'ent.catalog.order.wizard'
    _description = 'Catalog Order Wizard'

    catalog_item_id = fields.Many2one('ent.catalog.item', required=True, readonly=True)
    quantity = fields.Float('Quantity Needed', default=1.0, required=True)
    
    def action_confirm_order(self):
        item = self.catalog_item_id
        lines = item.vendor_line_ids
        
        if not lines:
            raise UserError("No active vendors found for this item.")
            
        # --- SMART ALLOCATION ROUTER ---
        strategy = lines[0].allocation_strategy
        if strategy == 'ranked':
            # Always pick the highest ranked vendor (lowest number)
            selected_line = lines.sorted(key=lambda l: l.award_rank)[0]
        else:
            # Equal Division: Randomly assign to distribute the purchasing volume evenly
            selected_line = random.choice(lines)

        # Generate the RO with the specifically allocated vendor's price!
        ro = self.env['ent.request.order'].create({
            'request_title': f"Catalog Order: {item.name}",
            'state': 'draft',
            'line_ids': [(0, 0, {
                'name': item.name,
                'quantity': self.quantity,
                'uom_id': item.uom_id.id,
                'estimated_price': selected_line.price_unit,
            })]
        })
        
        return {
            'name': 'Request Order',
            'type': 'ir.actions.act_window',
            'res_model': 'ent.request.order',
            'res_id': ro.id,
            'view_mode': 'form',
            'target': 'current'
        }