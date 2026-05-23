from odoo import models, fields, api

class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    evaluation_ids = fields.One2many('ent.vendor.evaluation', 'picking_id', string='Vendor Evaluations')
    evaluation_count = fields.Integer(compute='_compute_evaluation_count')

    @api.depends('evaluation_ids')
    def _compute_evaluation_count(self):
        for picking in self:
            picking.evaluation_count = len(picking.evaluation_ids)

    def button_validate(self):
        # 1. Let Odoo do its normal warehouse validation first
        res = super(StockPickingInherit, self).button_validate()
        
        # 2. Intercept: Loop through validated receipts
        for picking in self:
            # Only trigger for Incoming Shipments (Receipts) linked to a Purchase Order
            if picking.picking_type_code == 'incoming' and picking.purchase_id:
                
                # Prevent duplicate evaluations if they validate multiple times (e.g., backorders)
                existing_eval = self.env['ent.vendor.evaluation'].search([('picking_id', '=', picking.id)])
                
                if not existing_eval:
                    # Silently generate the Draft Evaluation
                    self.env['ent.vendor.evaluation'].create({
                        'vendor_id': picking.partner_id.id,
                        'picking_id': picking.id,
                    })
        return res

    def action_view_evaluations(self):
        self.ensure_one()
        return {
            'name': 'Vendor Evaluation',
            'type': 'ir.actions.act_window',
            'res_model': 'ent.vendor.evaluation',
            'view_mode': 'tree,form',
            'domain': [('picking_id', '=', self.id)],
            'context': {'default_picking_id': self.id, 'default_vendor_id': self.partner_id.id},
        }