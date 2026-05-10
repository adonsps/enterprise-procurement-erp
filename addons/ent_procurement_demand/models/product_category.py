from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'  # This tells Odoo to merge our code into the existing table

    procurement_pic_id = fields.Many2one('res.users', string='Default Procurement PIC', 
                                         help="The buyer responsible for managing requests in this category.")
    
    requires_two_envelope = fields.Boolean(string='Requires Two-Envelope Tender', default=False, 
                                           help="If checked, ROs in this category will enforce strict technical/commercial separation.")