from odoo import models, fields, api

class ProcurementCatalogItem(models.Model):
    _name = 'ent.catalog.item'
    _description = 'Outline Agreement Catalog Item'
    _order = 'name asc'

    # The original product definition
    product_id = fields.Many2one('product.product', string='Product / Material', required=True)
    name = fields.Char(related='product_id.name', string='Item Name', store=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    
    # Contract linkages
    vendor_id = fields.Many2one('res.partner', string='Contracted Vendor', required=True)
    contract_id = fields.Many2one('ent.contract', string='Outline Agreement (PPH)', required=True, ondelete='cascade')
    
    # Locked Pricing
    price_unit = fields.Monetary(string='Locked Price', currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', related='contract_id.company_id.currency_id')
    
    # Catalog Status
    active = fields.Boolean('Active', default=True)

    def action_create_ro_from_catalog(self):
        # We will build a popup wizard here next so the user can input their desired Quantity 
        # and instantly generate a locked Request Order!
        pass