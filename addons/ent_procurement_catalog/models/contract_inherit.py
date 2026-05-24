from odoo import models, fields

class ContractInherit(models.Model):
    _inherit = 'ent.contract'
    # Changed to point to the new vendor lines table
    catalog_item_ids = fields.One2many('ent.catalog.vendor.line', 'contract_id', string='Outline Agreement Items')