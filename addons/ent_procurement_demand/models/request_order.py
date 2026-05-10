import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

class RequestOrder(models.Model):
    _name = 'ent.request.order'
    _description = 'Procurement Request Order'

    # Core Information
    name = fields.Char(string='RO Number', required=True, copy=False, default='New')
    request_title = fields.Char(string='Request Title', required=True)
    department = fields.Char(string='Department')
    requestor_id = fields.Many2one('res.users', string='Requestor', default=lambda self: self.env.user)
    
    # Category & Routing
    category_id = fields.Many2one('product.category', string='Procurement Category')
    pic_id = fields.Many2one('res.users', string='Procurement PIC', readonly=True)

    # Financials & Docs
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    estimated_budget = fields.Monetary(string='Total Estimated Budget', compute='_compute_total_budget', store=True, currency_field='currency_id')
    
    description = fields.Text(string='Justification & Specs')
    tor_filename = fields.Char(string='TOR Filename')
    tor_attachment = fields.Binary(string='Terms of Reference (TOR)', attachment=True)
    
    # --- NEW: The Line Items Relationship ---
    line_ids = fields.One2many('ent.request.order.line', 'ro_id', string='Request Lines')

    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('ent.request.order') or 'New'
        return super().create(vals_list)

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id and self.category_id.procurement_pic_id:
            self.pic_id = self.category_id.procurement_pic_id
        else:
            self.pic_id = False

    # --- NEW: Auto-calculate the header budget based on the lines ---
    @api.depends('line_ids.subtotal')
    def _compute_total_budget(self):
        for rec in self:
            rec.estimated_budget = sum(line.subtotal for line in rec.line_ids)

    # --- NEW: The AI Trigger Placeholder ---
    def action_suggest_category_ai(self):
        for rec in self:
            # 1. Fetch the API Key from System Parameters
            api_key = self.env['ir.config_parameter'].sudo().get_param('gemini.api_key')
            if not api_key:
                raise UserError("Please configure 'gemini.api_key' in Settings -> Technical -> System Parameters.")

            # 2. Fetch all Level 3 Categories (Categories that have NO children)
            leaf_categories = self.env['product.category'].search([('child_id', '=', False)])
            if not leaf_categories:
                raise UserError("No Level 3 categories found in the taxonomy.")

            # Format the categories into a readable list for the LLM
            cat_options = "\n".join([f"ID {c.id}: {c.display_name}" for c in leaf_categories])

            # 3. Construct the Prompt
            prompt = f"""
            You are an expert Procurement Category Manager. Analyze the following request and select the absolute best matching Level 3 Category ID from the provided list.
            
            Request Title: {rec.request_title or 'N/A'}
            Justification & Specs: {rec.description or 'N/A'}
            
            Available Level 3 Categories:
            {cat_options}
            
            CRITICAL: Respond ONLY with the numerical ID of the best matching category. Do not include any other text, explanation, or punctuation.
            """

            # 4. Call the Gemini REST API (Updated Endpoint)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.0} # Set to 0.0 for maximum analytical precision
            }
            headers = {'Content-Type': 'application/json'}

            try:
                response = requests.post(url, json=payload, headers=headers)
                
                # NEW: Advanced Error Capture
                if not response.ok:
                    # If Google rejects it, show the actual Google error text in Odoo
                    raise UserError(f"Google API Error {response.status_code}:\n{response.text}")
                    
                result = response.json()
                
                # Parse the response text
                llm_output = result['candidates'][0]['content']['parts'][0]['text'].strip()
                
                # Sanitize output (extract only numbers)
                suggested_id = int(''.join(filter(str.isdigit, llm_output)))
                
                # 5. Apply the mapped Category ID to the Request Order
                suggested_category = self.env['product.category'].browse(suggested_id)
                if suggested_category.exists():
                    rec.category_id = suggested_category.id
                    # Manually trigger the PIC assignment logic
                    rec._onchange_category_id() 
                else:
                    raise UserError(f"AI returned an invalid Category ID: {suggested_id}")
                    
            except requests.exceptions.RequestException as e:
                raise UserError(f"Network error communicating with Gemini API: {str(e)}")
            except (KeyError, IndexError, ValueError):
                raise UserError(f"Failed to parse Gemini API response. Raw output from AI: {result}")

    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'
            
    def action_approve(self):
        for rec in self:
            rec.state = 'approved'

# --- NEW: The Line Items Database Table ---
class RequestOrderLine(models.Model):
    _name = 'ent.request.order.line'
    _description = 'Request Order Line Item'

    ro_id = fields.Many2one('ent.request.order', string='Request Order Reference', required=True, ondelete='cascade')
    name = fields.Char(string='Item Description / Spec', required=True)
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    
    currency_id = fields.Many2one(related='ro_id.currency_id')
    estimated_price = fields.Monetary(string='Est. Unit Price', currency_field='currency_id')
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', store=True, currency_field='currency_id')

    @api.depends('quantity', 'estimated_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.estimated_price