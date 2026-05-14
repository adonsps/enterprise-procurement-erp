from odoo import models, fields, api
from odoo.exceptions import UserError
import base64

class TenderBidInherit(models.Model):
    _inherit = 'ent.tender.bid'

    generate_contract = fields.Boolean(string='Generate Contract on Award', default=False)
    contract_type = fields.Selection([
        ('outline', 'Outline Agreement (Price Lock)'),
        ('pks', 'Perjanjian Kerja Sama (PKS)'),
        ('pjk', 'Perjanjian Jasa Konstruksi (PJK)')
    ], string='Contract Template')
    
    contract_id = fields.Many2one('ent.contract', string='Generated Contract', readonly=True)

    def _execute_contract_generation(self):
        for bid in self:
            if not bid.contract_type:
                raise UserError("Please select a Contract Template type.")
            if bid.contract_id:
                raise UserError("A contract has already been generated for this vendor.")

            template_name = dict(self._fields['contract_type'].selection).get(bid.contract_type)
            contract = self.env['ent.contract'].create({
                'title': f"{template_name} - {bid.tender_id.title}",
                'vendor_id': bid.vendor_id.id,
                'po_id': bid.po_id.id if bid.po_id else False,
                'contract_value': bid.commercial_price,
                'start_date': fields.Date.today(),
                'end_date': fields.Date.today(), 
                'contract_type': bid.contract_type,
                'state': 'draft'
            })
            bid.contract_id = contract.id

            if not HAS_DOCX:
                raise UserError("The python-docx library is missing! Run: pip install python-docx")

            doc = Document()
            
            if bid.contract_type == 'outline':
                # Setup 2-column layout table for headers and paragraphs
                layout = doc.add_table(rows=0, cols=2)
                layout.autofit = True
                
                # Title
                row = layout.add_row().cells
                row[0].text = "PERJANJIAN PENGIKATAN HARGA\nRef Kontrak: " + contract.name
                row[1].text = "OUTLINE AGREEMENT\nContract Ref: " + contract.name
                
                # Space
                layout.add_row()

                # Parties
                row = layout.add_row().cells
                row[0].text = f"Antara:\nKawan Lama Group (Pembeli)\n{bid.vendor_id.name} (Vendor)"
                row[1].text = f"Between:\nKawan Lama Group (Buyer)\n{bid.vendor_id.name} (Vendor)"

                layout.add_row()

                # Article 1
                row = layout.add_row().cells
                row[0].text = "Pasal 1: Ruang Lingkup & Pengikatan Harga\nPerjanjian Pengikatan Harga ini mengikat Harga Satuan dari item yang terdaftar. Kuantitas yang tercantum hanya merupakan perkiraan. Pembeli tidak memiliki komitmen hukum untuk membeli kuantitas minimum."
                row[1].text = "Article 1: Scope & Price Lock\nThis Outline Agreement locks the Unit Prices of the listed items. The quantities listed are forecasts only. The Buyer has no legal commitment to purchase minimum quantities."

                doc.add_paragraph("\n") # Break outside the layout table for the data table
                
                # Add the Full-Width Pricing Table
                table = doc.add_table(rows=1, cols=3)
                table.style = 'Table Grid'
                hdr_cells = table.rows[0].cells
                hdr_cells[0].text = 'Deskripsi / Item'
                hdr_cells[1].text = 'Satuan / UoM'
                hdr_cells[2].text = 'Harga Satuan / Locked Unit Price'
                
                for line in bid.bid_line_ids:
                    row_cells = table.add_row().cells
                    row_cells[0].text = str(line.name)
                    row_cells[1].text = str(line.uom_id.name)
                    row_cells[2].text = f"{line.price_unit:,.2f} {bid.currency_id.name}"
                
                doc.add_paragraph(f"\n*Nilai Referensi Total / Total Reference Value: {bid.commercial_price:,.2f} {bid.currency_id.name}").style.font.italic = True

                # Back to 2-column layout for Article 2
                layout2 = doc.add_table(rows=0, cols=2)
                row = layout2.add_row().cells
                row[0].text = "Pasal 2: Perlindungan Pembeli & Pengakhiran\n2.1 Pengakhiran: Pembeli berhak mengakhiri perjanjian ini kapan saja dengan pemberitahuan tertulis 30 hari sebelumnya tanpa denda apapun.\n\n2.2 Penyesuaian Harga: Jika harga pasar untuk item turun di bawah harga yang diikat, Vendor setuju untuk menyamakan dengan harga pasar yang lebih rendah."
                row[1].text = "Article 2: Buyer Protection & Termination\n2.1 Termination: The Buyer reserves the right to terminate this agreement at any time with 30 days prior written notice without any penalty.\n\n2.2 Price Matching: If market prices for the items fall below the locked prices, the Vendor agrees to match the lower market price."
            
            else:
                doc.add_heading(f"{template_name.upper()}", 0)
                doc.add_paragraph(f"Contract Ref: {contract.name}\nFirst Party: Kawan Lama Group\nSecond Party: {bid.vendor_id.name}")
                doc.add_paragraph(f"Total Valuation: {bid.commercial_price:,.2f} {bid.currency_id.name}")

            # Save and Attach
            file_stream = io.BytesIO()
            doc.save(file_stream)
            file_content = file_stream.getvalue()
            
            self.env['ir.attachment'].create({
                'name': f"{contract.name}_{bid.contract_type}_Draft.docx",
                'type': 'binary',
                'datas': base64.b64encode(file_content),
                'res_model': 'ent.contract',
                'res_id': contract.id,
            })

            # PDF Generation
            pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf('ent_procurement_clm.action_report_contract_pdf', [contract.id])
            self.env['ir.attachment'].create({
                'name': f"{contract.name}_{bid.contract_type}_Draft.pdf",
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'ent.contract',
                'res_id': contract.id,
            })

    def action_award_bid(self):
        # 1. Execute the original PO Awarding logic
        res = super(TenderBidInherit, self).action_award_bid()
        
        # 2. Automatically generate if the checkbox was toggled
        for bid in self:
            if bid.generate_contract and bid.contract_type:
                bid._execute_contract_generation()
        return res

    def action_generate_contract_manual(self):
        # Fallback button for the PIC if they forgot
        self._execute_contract_generation()