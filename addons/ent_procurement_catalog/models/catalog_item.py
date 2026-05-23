from odoo import models, fields, api

class ProcurementCatalogItem(models.Model):
    _name = 'ent.catalog.item'
    _description = 'Outline Agreement Catalog Item'
    _order = 'name asc'

    product_id = fields.Many2one('product.product', string='Product / Material', required=True)
    name = fields.Char(related='product_id.name', string='Item Name', store=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    
    vendor_id = fields.Many2one('res.partner', string='Contracted Vendor', required=True)
    contract_id = fields.Many2one('ent.contract', string='Outline Agreement (PPH)', required=True, ondelete='cascade')
    
    price_unit = fields.Monetary(string='Locked Price', currency_field='currency_id', required=True)
    
    # FIX: Define company locally and pull currency from the current environment
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    
    active = fields.Boolean('Active', default=True)

    def action_create_ro_from_catalog(self):
        # Opens the popup wizard
        return {
            'name': 'Specify Quantity',
            'type': 'ir.actions.act_window',
            'res_model': 'ent.catalog.order.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_catalog_item_id': self.id}
        }

class ProcurementCatalogWizard(models.TransientModel):
    _name = 'ent.catalog.order.wizard'
    _description = 'Catalog Order Wizard'

    catalog_item_id = fields.Many2one('ent.catalog.item', required=True, readonly=True)
    quantity = fields.Float('Quantity Needed', default=1.0, required=True)
    uom_id = fields.Many2one(related='catalog_item_id.uom_id')
    price_unit = fields.Monetary(related='catalog_item_id.price_unit')
    currency_id = fields.Many2one(related='catalog_item_id.currency_id')

    def action_confirm_order(self):
        # NOTE: If your ent_procurement_demand module uses a different name for the 
        # RO lines (like 'ro_line_ids'), change 'line_ids' below to match your exact field name!
        ro = self.env['ent.request.order'].create({
            'title': f"Catalog Order: {self.catalog_item_id.name}",
            'state': 'draft',
            'line_ids': [(0, 0, {
                'product_id': self.catalog_item_id.product_id.id,
                'name': self.catalog_item_id.name,
                'product_qty': self.quantity,
                'uom_id': self.catalog_item_id.uom_id.id,
                'estimated_price': self.catalog_item_id.price_unit,
            })]
        })
        
        # Instantly open the newly created RO for the user
        return {
            'name': 'Request Order',
            'type': 'ir.actions.act_window',
            'res_model': 'ent.request.order',
            'res_id': ro.id,
            'view_mode': 'form',
            'target': 'current'
        }