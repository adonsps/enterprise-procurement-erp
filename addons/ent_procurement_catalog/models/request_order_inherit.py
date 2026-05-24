from odoo import models, fields, api
from odoo.exceptions import UserError
import math

class RequestOrderLineInherit(models.Model):
    _inherit = 'ent.request.order.line'

    catalog_item_id = fields.Many2one('ent.catalog.item', string='Linked Catalog Item')

class RequestOrderInherit(models.Model):
    _inherit = 'ent.request.order'

    def action_approve(self):
        # 1. Let the core Demand module approve the RO first
        res = super().action_approve()
        
        # 2. Intercept: Process Catalog Items into Purchase Orders
        for ro in self:
            po_lines_by_vendor = {}
            catalog_lines = ro.line_ids.filtered(lambda l: l.catalog_item_id)
            
            for line in catalog_lines:
                self._allocate_catalog_po(line, po_lines_by_vendor)
            
            # 3. Generate and Auto-Confirm the Purchase Orders!
            for vendor_id, lines_data in po_lines_by_vendor.items():
                po = self.env['purchase.order'].create({
                    'partner_id': vendor_id,
                    'origin': ro.name,
                    'order_line': [(0, 0, ld) for ld in lines_data]
                })
                # Auto-confirm bypasses sourcing
                po.button_confirm()
                
        return res

    def _allocate_catalog_po(self, line, po_lines_by_vendor):
        qty_needed = line.quantity
        today = fields.Date.today()
        
        # Get Valid Vendors: Active Contract, Not Expired, Remaining Capacity > 0
        valid_vendors = line.catalog_item_id.vendor_line_ids.filtered(
            lambda v: v.contract_id.state == 'active' 
                      and (not v.contract_id.end_date or v.contract_id.end_date >= today)
                      and v.remaining_qty > 0
        )
        
        if not valid_vendors:
            raise UserError(f"Cannot process '{line.name}'. There are no active Outline Agreements with remaining capacity.")

        strategy = valid_vendors[0].allocation_strategy
        
        # SCENARIO A: RANKED BASED
        if strategy == 'ranked':
            # Highest rank (Lowest number) first
            valid_vendors = valid_vendors.sorted(key=lambda v: v.award_rank)
            
            for vendor_line in valid_vendors:
                if qty_needed <= 0:
                    break
                
                allocate_qty = min(qty_needed, vendor_line.remaining_qty)
                self._add_to_po_dict(po_lines_by_vendor, vendor_line, line, allocate_qty)
                
                # Deduct from the Outline Agreement Limit
                vendor_line.remaining_qty -= allocate_qty
                qty_needed -= allocate_qty
                
            if qty_needed > 0:
                raise UserError(f"Insufficient total contract capacity! You are short by {qty_needed} for {line.name}.")
                
        # SCENARIO B: EQUAL SHARE
        elif strategy == 'equal':
            num_vendors = len(valid_vendors)
            base_qty = math.floor(qty_needed / num_vendors)
            remainder = qty_needed % num_vendors
            
            # Tie Breaker: Highest VPE Score gets the odd remainder!
            valid_vendors = valid_vendors.sorted(key=lambda v: v.vendor_id.vpe_trust_score, reverse=True)
            
            for vendor_line in valid_vendors:
                allocate_qty = base_qty
                if remainder > 0:
                    allocate_qty += 1
                    remainder -= 1
                    
                if allocate_qty > 0:
                    if allocate_qty > vendor_line.remaining_qty:
                        raise UserError(f"Vendor '{vendor_line.vendor_id.name}' lacks capacity ({vendor_line.remaining_qty} left) to fulfill their equal share of {allocate_qty} for '{line.name}'.")
                        
                    self._add_to_po_dict(po_lines_by_vendor, vendor_line, line, allocate_qty)
                    # Deduct from the Outline Agreement Limit
                    vendor_line.remaining_qty -= allocate_qty

    def _add_to_po_dict(self, po_lines_by_vendor, vendor_line, ro_line, qty):
        vendor_id = vendor_line.vendor_id.id
        if vendor_id not in po_lines_by_vendor:
            po_lines_by_vendor[vendor_id] = []
            
        po_lines_by_vendor[vendor_id].append({
            'name': ro_line.name,
            'product_id': vendor_line.catalog_item_id.product_id.id,
            'product_qty': qty,
            'product_uom': ro_line.uom_id.id,
            'price_unit': vendor_line.price_unit,
            'date_planned': fields.Datetime.now(),
        })