from odoo import models, fields

class ContractInherit(models.Model):
    _inherit = 'ent.contract'

    # This creates the backward link so the Contract can see its Catalog Items!
    catalog_item_ids = fields.One2many('ent.catalog.item', 'contract_id', string='Outline Agreement Items')