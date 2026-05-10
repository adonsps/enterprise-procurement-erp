from odoo import models, fields, api

class ProductCategory(models.Model):
    _inherit = 'product.category'

    procurement_pic_id = fields.Many2one('res.users', string='Default Procurement PIC', 
                                         help="The buyer responsible for managing requests in this category.")
    
    requires_two_envelope = fields.Boolean(string='Requires Two-Envelope Tender', default=False, 
                                           help="If checked, ROs in this category will enforce strict technical/commercial separation.")

    # Override the display name calculation
    def _compute_display_name(self):
        # If the UI sends the 'short_category_name' flag, only show the Level 3 name
        if self.env.context.get('short_category_name'):
            for category in self:
                category.display_name = category.name
        else:
            # Otherwise, show the normal long path (Level 1 / Level 2 / Level 3)
            super()._compute_display_name()