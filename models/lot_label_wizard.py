from odoo import models, fields, api, _ # type: ignore
from odoo.exceptions import UserError # type: ignore
import base64

class LotLabelWizard(models.TransientModel):
    _name = 'lot.label.wizard'
    _description = 'Lot Label Print Wizard'

    lot_ids = fields.Many2many(
        'stock.lot',
        string='Lots',
        required=True
    )
    
    label_count = fields.Integer(
        string='Number of Labels',
        default=1,
        required=True,
        help="Number of identical labels to print for each lot"
    )

    @api.constrains('label_count')
    def _check_label_count(self):
        for record in self:
            if record.label_count < 1:
                raise UserError(_("Number of labels must be at least 1"))
            if record.label_count > 50:  # Reasonable limit
                raise UserError(_("Number of labels cannot exceed 50"))

    def action_print_labels(self):
        """Print labels with specified count"""
        if not self.lot_ids:
            raise UserError(_("No lots selected for printing"))
        
        # Pass the label count to the report context
        return self.env.ref('custom_rsfp_module.action_report_lot_label_custom').with_context(
            label_count=self.label_count,
            # (Optional but recommended) Explicitly expose range to QWeb context
            range=range,
        ).report_action(self.lot_ids)
    
    # def action_generate_zpl(self):
    #     """Generate ZPL file for selected lots for TSC TE244 (100x50mm)"""
    #     if not self.lot_ids:
    #         raise UserError(_("No lots selected for printing"))

    #     zpl_content = ""
        
    #     # 100mm x 50mm at 203 DPI is approx 800 dots x 400 dots
    #     for lot in self.lot_ids:
    #         # 1. Gather Data
    #         product_name = lot.product_id.name or ""
    #         # Sanitize: Remove characters that might break ZPL
    #         product_name = product_name.replace('^', '').replace('~', '')
            
    #         lot_name = lot.name or ""
            
    #         # Get PO Info using your existing helper method
    #         po_info = lot._get_purchase_order_info()
    #         po_str = f"PO: {po_info.get('po_number', 'N/A')}"
    #         vendor_str = f"Ven: {po_info.get('vendor', 'N/A')}"
            
    #         # Qty Info
    #         qty_str = f"Qty: {lot.product_qty} {lot.product_uom_id.name}"
            
    #         # 2. Construct ZPL
    #         # ^XA = Start
    #         # ^PW800 = Width 800 dots (100mm)
    #         # ^LL400 = Length 400 dots (50mm)
    #         # ^CI28 = UTF-8 Encoding
    #         label_zpl = "^XA^CI28^PW800^LL400"
            
    #         # Product Name (Top, Centered, Wrapped in a box 760 dots wide)
    #         # ^FO20,20 = Position X=20, Y=20
    #         # ^A0N,35,35 = Font 0, Height 35
    #         # ^FB760,2... = Field Block width 760, max 2 lines, center align
    #         label_zpl += f"^FO20,20^A0N,35,35^FB760,2,0,C,0^FD{product_name}^FS"
            
    #         # Lot Name (Below Product)
    #         label_zpl += f"^FO20,100^A0N,30,30^FB760,1,0,C,0^FDLN: {lot_name}^FS"
            
    #         # Barcode (Code 128)
    #         # ^BY2 = Module width 2 dots
    #         # ^BCN,80... = Code 128, Height 80 dots
    #         label_zpl += f"^FO150,140^BY2^BCN,80,Y,N,N^FD{lot_name}^FS"
            
    #         # Details (PO, Vendor, Qty) - Bottom Left
    #         label_zpl += f"^FO20,260^A0N,25,25^FD{po_str}^FS"
    #         label_zpl += f"^FO20,290^A0N,25,25^FD{vendor_str}^FS"
    #         label_zpl += f"^FO20,320^A0N,25,25^FD{qty_str}^FS"
            
    #         # End Label
    #         label_zpl += "^XZ\n"

    #         # Repeat for the requested number of labels
    #         for _ in range(self.label_count):
    #             zpl_content += label_zpl

    #     # 3. Create Attachment
    #     filename = "labels.zpl"
    #     attachment = self.env['ir.attachment'].create({
    #         'name': filename,
    #         'type': 'binary',
    #         'datas': base64.b64encode(zpl_content.encode('utf-8')),
    #         'res_model': 'lot.label.wizard',
    #         'res_id': self.id,
    #         'mimetype': 'text/plain',
    #     })

    #     # 4. Trigger Download
    #     return {
    #         'type': 'ir.actions.act_url',
    #         'url': f'/web/content/{attachment.id}?download=true',
    #         'target': 'self',
    #     }



    # def action_generate_zpl(self):
    #     """Generate ZPL and trigger client-side printing"""
    #     if not self.lot_ids:
    #         raise UserError(_("No lots selected for printing"))

    #     zpl_content = ""
        
    #     for lot in self.lot_ids:
    #         # --- Data Gathering ---
    #         product_name = (lot.product_id.name or "").replace('^', '').replace('~', '')
    #         lot_name = lot.name or ""
            
    #         # Get PO Info
    #         po_info = lot._get_purchase_order_info()
    #         po_str = f"PO: {po_info.get('po_number', 'N/A')}"
    #         vendor_str = f"Ven: {po_info.get('vendor', 'N/A')}"
    #         qty_str = f"Qty: {lot.product_qty} {lot.product_uom_id.name}"
            
    #         # --- ZPL Construction (100x50mm) ---
    #         label_zpl = "^XA^CI28^PW800^LL400"
            
    #         # Product Name
    #         label_zpl += f"^FO20,20^A0N,35,35^FB760,2,0,C,0^FD{product_name}^FS"
            
    #         # Lot Name
    #         label_zpl += f"^FO20,100^A0N,30,30^FB760,1,0,C,0^FDLN: {lot_name}^FS"
            
    #         # Barcode (Code 128)
    #         label_zpl += f"^FO150,140^BY2^BCN,80,Y,N,N^FD{lot_name}^FS"
            
    #         # Details
    #         label_zpl += f"^FO20,260^A0N,25,25^FD{po_str}^FS"
    #         label_zpl += f"^FO20,290^A0N,25,25^FD{vendor_str}^FS"
    #         label_zpl += f"^FO20,320^A0N,25,25^FD{qty_str}^FS"
            
    #         label_zpl += "^XZ\n"

    #         for _ in range(self.label_count):
    #             zpl_content += label_zpl

    #     # --- Return Client Action ---
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'custom_rsfp_module.print_zpl_action',
    #         'params': {
    #             'zpl_data': zpl_content,
    #         }
    #     }




    # def action_generate_zpl(self):
    #     """Generate ZPL and trigger client-side printing"""
    #     if not self.lot_ids:
    #         raise UserError(_("No lots selected for printing"))

    #     zpl_content = ""
        
    #     for lot in self.lot_ids:
    #         # Common Data
    #         product_name = (lot.product_id.name or "").replace('^', '').replace('~', '')
    #         lot_name = lot.name or ""
    #         qty_str = f"{lot.product_qty} {lot.product_uom_id.name}"
            
    #         # Start Label
    #         # ^XA = Start, ^CI28 = UTF-8, ^PW800 = 100mm width, ^LL400 = 50mm length
    #         label_zpl = "^XA^CI28^PW800^LL400"

    #         if not lot.parent_lot_id:
    #             # === CASE 1: PARENT LOT (Bulk/Raw) ===
    #             # Matches the "if not lot.parent_lot_id" block in your XML
                
    #             # 1. Barcode (Top Centered)
    #             # ^FO150,20 = Position X=150, Y=20
    #             # ^BY2 = Module width
    #             # ^BCN,60,Y,N,N = Code 128, Height 60, Print interpretation line
    #             label_zpl += f"^FO150,20^BY2^BCN,60,Y,N,N^FD{lot_name}^FS"
                
    #             # 2. Lot Name (Bold)
    #             label_zpl += f"^FO20,100^A0N,30,30^FB760,1,0,C,0^FD{lot_name}^FS"
                
    #             # 3. Product & Qty
    #             label_zpl += f"^FO20,135^A0N,25,25^FB760,1,0,C,0^FDProd: {product_name}^FS"
    #             label_zpl += f"^FO20,165^A0N,25,25^FB760,1,0,C,0^FDQty: {qty_str}^FS"
                
    #             # 4. Separator Line
    #             label_zpl += f"^FO20,195^GB760,1,1^FS"
                
    #             # 5. Purchase Info
    #             po_info = lot._get_purchase_order_info() or {}
    #             po_num = po_info.get('po_number', 'N/A')
    #             vendor = po_info.get('vendor', 'N/A')
    #             rec_date = po_info.get('received_date', 'N/A')
                
    #             po_text = f"PO: {po_num} | Vendor: {vendor}"
    #             rec_text = f"Received: {rec_date}"
                
    #             label_zpl += f"^FO20,205^A0N,22,22^FB760,1,0,C,0^FD{po_text}^FS"
    #             label_zpl += f"^FO20,230^A0N,22,22^FB760,1,0,C,0^FD{rec_text}^FS"
                
    #             # 6. Separator Line
    #             label_zpl += f"^FO20,260^GB760,1,1^FS"
                
    #             # 7. Footer (Created Date & Status)
    #             create_date = lot.create_date.strftime('%d/%m/%Y %H:%M') if lot.create_date else 'N/A'
    #             label_zpl += f"^FO20,270^A0N,20,20^FB760,1,0,C,0^FDCreated: {create_date}^FS"
    #             label_zpl += f"^FO20,295^A0N,20,20^FB760,1,0,C,0^FDReady for Sorting/Quality Testing^FS"

    #         else:
    #             # === CASE 2: CHILD LOT (Graded/Sorted) ===
    #             # Matches the "else" block in your XML
                
    #             # 1. Barcode (Top Centered)
    #             label_zpl += f"^FO150,20^BY2^BCN,60,Y,N,N^FD{lot_name}^FS"
                
    #             # 2. Lot Name (Larger/Bold)
    #             label_zpl += f"^FO20,100^A0N,35,35^FB760,1,0,C,0^FD{lot_name}^FS"
                
    #             # 3. Product
    #             label_zpl += f"^FO20,145^A0N,25,25^FB760,1,0,C,0^FDProduct: {product_name}^FS"
                
    #             # 4. Parent Lot
    #             parent_name = lot.parent_lot_id.name or ""
    #             label_zpl += f"^FO20,175^A0N,25,25^FB760,1,0,C,0^FDParent Lot: {parent_name}^FS"
                
    #             # 5. Quantity (Bold/Larger)
    #             label_zpl += f"^FO20,210^A0N,30,30^FB760,1,0,C,0^FDQty: {qty_str}^FS"
                
    #             # 6. Processing Info
    #             proc_info = lot._get_processing_info() or {}
    #             sorted_date = proc_info.get('sorted_date', 'N/A')
    #             report_name = proc_info.get('sorting_report_name', 'N/A')
                
    #             info_text = f"Sorted: {sorted_date} | Report: {report_name}"
                
    #             label_zpl += f"^FO20,250^A0N,22,22^FB760,2,0,C,0^FD{info_text}^FS"

    #         # End Label
    #         label_zpl += "^XZ\n"

    #         for _ in range(self.label_count):
    #             zpl_content += label_zpl

    #     # --- Return Client Action ---
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'custom_rsfp_module.print_zpl_action',
    #         'params': {
    #             'zpl_data': zpl_content,
    #         }
    #     }
    

    # def action_generate_zpl(self):
    #     """Generate ZPL and trigger client-side printing"""
    #     if not self.lot_ids:
    #         raise UserError(_("No lots selected for printing"))

    #     zpl_content = ""
        
    #     for lot in self.lot_ids:
    #         # Common Data
    #         product_name = (lot.product_id.name or "").replace('^', '').replace('~', '')
    #         lot_name = lot.name or ""
    #         qty_str = f"{lot.product_qty} {lot.product_uom_id.name}"
            
    #         # Start Label - 100mm x 50mm at 203 DPI = 812 x 406 dots
    #         label_zpl = "^XA^CI28^PW812^LL406"

    #         if not lot.parent_lot_id:
    #             # === CASE 1: PARENT LOT (Bulk/Raw) ===
                
    #             # 1. Product Name (Top, smaller font to fit better)
    #             label_zpl += f"^FO50,15^A0N,28,28^FB712,2,0,C,0^FD{product_name}^FS"
                
    #             # 2. Lot Name (Bold, centered) - SINGLE OCCURRENCE
    #             # label_zpl += f"^FO50,70^A0N,35,35^FB712,1,0,C,0^FD{lot_name}^FS"
    #             label_zpl += f"^FO35,70^A0N,35,35^FB712,1,0,C,0^FD{lot_name}^FS"
                
    #             # 3. Barcode (Centered below lot name)
    #             label_zpl += f"^FO256,110^BY2^BCN,80,N,N,N^FD{lot_name}^FS"
                
    #             # 4. Quantity (Below barcode)
    #             label_zpl += f"^FO50,175^A0N,25,25^FB712,1,0,C,0^FDQty: {qty_str}^FS"
                
    #             # 5. Purchase Info (Compact layout)
    #             po_info = lot._get_purchase_order_info() or {}
    #             po_num = po_info.get('po_number', 'N/A')
    #             vendor = po_info.get('vendor', 'N/A')
    #             rec_date = po_info.get('received_date', 'N/A')
                
    #             # Split info into two compact lines
    #             label_zpl += f"^FO50,205^A0N,20,20^FB712,1,0,C,0^FDPO: {po_num} | Vendor: {vendor}^FS"
    #             label_zpl += f"^FO50,230^A0N,20,20^FB712,1,0,C,0^FDReceived: {rec_date}^FS"
                
    #             # 6. Separator line
    #             label_zpl += f"^FO50,255^GB712,1,1^FS"
                
    #             # 7. Footer (Status)
    #             label_zpl += f"^FO50,265^A0N,18,18^FB712,2,0,C,0^FDReady for Sorting/Quality Testing^FS"

    #         else:
    #             # === CASE 2: CHILD LOT (Graded/Sorted) ===
                
    #             # 1. Product Name (Top)
    #             label_zpl += f"^FO50,15^A0N,28,28^FB712,2,0,C,0^FD{product_name}^FS"
                
    #             # 2. Lot Name (Bold, centered) - SINGLE OCCURRENCE
    #             label_zpl += f"^FO50,70^A0N,35,35^FB712,1,0,C,0^FD{lot_name}^FS"
                
    #             # 3. Barcode (Centered)
    #             label_zpl += f"^FO256,110^BY2^BCN,50,Y,N,N^FD{lot_name}^FS"
                
    #             # 4. Parent Lot & Quantity (Side by side)
    #             parent_name = lot.parent_lot_id.name or ""
    #             label_zpl += f"^FO50,175^A0N,22,22^FB350,1,0,L,0^FDParent: {parent_name}^FS"
    #             label_zpl += f"^FO412,175^A0N,22,22^FB300,1,0,R,0^FDQty: {qty_str}^FS"
                
    #             # 5. Processing Info (Compact)
    #             proc_info = lot._get_processing_info() or {}
    #             sorted_date = proc_info.get('sorted_date', 'N/A')
    #             report_name = proc_info.get('sorting_report_name', 'N/A')
                
    #             label_zpl += f"^FO50,205^A0N,20,20^FB712,1,0,C,0^FDSorted: {sorted_date}^FS"
    #             label_zpl += f"^FO50,230^A0N,20,20^FB712,1,0,C,0^FDReport: {report_name}^FS"
                
    #             # 6. Separator line
    #             label_zpl += f"^FO50,255^GB712,1,1^FS"
                
    #             # 7. Footer
    #             label_zpl += f"^FO50,265^A0N,18,18^FB712,2,0,C,0^FDGraded Product - Quality Tested^FS"

    #         # End Label
    #         label_zpl += "^XZ\n"

    #         for _ in range(self.label_count):
    #             zpl_content += label_zpl

    #     # Return Client Action
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'custom_rsfp_module.print_zpl_action',
    #         'params': {
    #             'zpl_data': zpl_content,
    #         }
    #     }

    # def action_generate_zpl(self):
    #     """Generate professional, high-clarity ZPL for 100x50mm labels"""
    #     if not self.lot_ids:
    #         raise UserError(_("No lots selected for printing"))

    #     zpl_content = ""
        
    #     for lot in self.lot_ids:
    #         # Data Sanitation
    #         product_name = (lot.product_id.name or "").replace('^', '').replace('~', '')[:60] # Cap length
    #         lot_name = lot.name or ""
    #         qty_str = f"{lot.product_qty} {lot.product_uom_id.name}"
            
    #         # Start Label (812x406 dots @ 203 DPI)
    #         # ^MTT = Thermal Transfer, ^MD15 = Darkness setting (adjust 0-30)
    #         label_zpl = "^XA^CI28^PW812^LL406^MTT^MD15"

    #         # --- TOP SECTION: PRODUCT IDENTIFICATION ---
    #         # Product Name: Bold, Left Aligned, wrapped up to 2 lines
    #         label_zpl += f"^FO50,30^A0N,35,35^FB712,2,0,L,0^FD{product_name}^FS"
            
    #         # Horizontal Divider
    #         label_zpl += "^FO50,110^GB712,3,3^FS"

    #         # --- MIDDLE SECTION: DYNAMIC CONTENT ---
    #         if not lot.parent_lot_id:
    #             # CASE 1: BULK/RAW LOT
    #             po_info = lot._get_purchase_order_info() or {}
                
    #             # Left Side: Key Details
    #             label_zpl += f"^FO50,140^A0N,24,24^FDPO: {po_info.get('po_number', 'N/A')}^FS"
    #             label_zpl += f"^FO50,180^A0N,24,24^FDVendor: {po_info.get('vendor', 'N/A')[:25]}^FS"
    #             label_zpl += f"^FO50,220^A0N,24,24^FDReceived: {po_info.get('received_date', 'N/A')}^FS"
                
    #             # Right Side: Large Quantity Block
    #             label_zpl += f"^FO500,140^A0N,20,20^FDTOTAL QTY^FS"
    #             label_zpl += f"^FO500,165^A0N,40,40^FD{qty_str}^FS"
                
    #             # Bottom Barcode (Clean, no text under it to avoid clutter)
    #             label_zpl += f"^FO500,230^BY2^BCN,80,N,N,N^FD{lot_name}^FS"
    #             label_zpl += f"^FO500,320^A0N,20,20^FB250,1,0,C^FD{lot_name}^FS"

    #         else:
    #             # CASE 2: GRADED/CHILD LOT
    #             proc_info = lot._get_processing_info() or {}
                
    #             # Left Side: Pedigree
    #             label_zpl += f"^FO50,140^A0N,22,22^FDParent Lot:^FS"
    #             label_zpl += f"^FO50,165^A0N,28,28^FD{lot.parent_lot_id.name}^FS"
    #             label_zpl += f"^FO50,210^A0N,22,22^FDSorted Date: {proc_info.get('sorted_date', 'N/A')}^FS"
    #             label_zpl += f"^FO50,240^A0N,22,22^FDReport: {proc_info.get('sorting_report_name', 'N/A')[:20]}^FS"
                
    #             # Right Side: Quantity
    #             label_zpl += f"^FO500,140^A0N,20,20^FDGRADED QTY^FS"
    #             label_zpl += f"^FO500,165^A0N,40,40^FD{qty_str}^FS"
                
    #             # Barcode
    #             label_zpl += f"^FO500,230^BY2^BCN,80,N,N,N^FD{lot_name}^FS"
    #             label_zpl += f"^FO500,320^A0N,20,20^FB250,1,0,C^FD{lot_name}^FS"

    #         # --- FOOTER SECTION ---
    #         # Dark Footer Bar
    #         label_zpl += "^FO50,350^GB712,40,40^FS"
    #         footer_text = "BULK RAW MATERIAL" if not lot.parent_lot_id else "QUALITY TESTED & GRADED"
    #         # Inverse text (White on Black)
    #         label_zpl += f"^FO50,360^A0N,25,25^FR^FB712,1,0,C,0^FD{footer_text}^FS"

    #         label_zpl += "^XZ\n"

    #         for _ in range(self.label_count):
    #             zpl_content += label_zpl

    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'custom_rsfp_module.print_zpl_action',
    #         'params': {'zpl_data': zpl_content}
    #     }

    # def action_generate_zpl(self):
    #     """Generate professional ZPL with Left-Aligned Barcode for 100x50mm labels"""
    #     if not self.lot_ids:
    #         raise UserError(_("No lots selected for printing"))

    #     zpl_content = ""
        
    #     for lot in self.lot_ids:
    #         # Data Sanitation
    #         product_name = (lot.product_id.name or "").replace('^', '').replace('~', '')[:60]
    #         lot_name = lot.name or ""
    #         qty_str = f"{lot.product_qty} {lot.product_uom_id.name}"
            
    #         # Start Label (812x406 dots @ 203 DPI)
    #         label_zpl = "^XA^CI28^PW812^LL406^MTT^MD15"

    #         # --- TOP SECTION: PRODUCT IDENTIFICATION ---
    #         # Product Name: Bold, Left Aligned
    #         label_zpl += f"^FO50,30^A0N,35,35^FB712,2,0,L,0^FD{product_name}^FS"
            
    #         # Horizontal Divider
    #         label_zpl += "^FO50,110^GB712,3,3^FS"

    #         # --- MIDDLE SECTION: BARCODE LEFT, DETAILS RIGHT ---
    #         # 1. Barcode (Left Aligned at X=50 to avoid edge cutting)
    #         # ^BCN,80,N = Code 128, 80 dot height, no human readable under barcode (placed manually below)
    #         label_zpl += f"^FO50,150^BY2^BCN,100,N,N,N^FD{lot_name}^FS"
    #         # Manually centered text under the barcode for better control
    #         label_zpl += f"^FO50,260^A0N,20,20^FB300,1,0,C^FD{lot_name}^FS"

    #         if not lot.parent_lot_id:
    #             # CASE 1: BULK/RAW LOT
    #             po_info = lot._get_purchase_order_info() or {}
                
    #             # Right Side Info Block (X=400)
    #             label_zpl += f"^FO400,140^A0N,22,22^FDPO: {po_info.get('po_number', 'N/A')}^FS"
    #             label_zpl += f"^FO400,175^A0N,22,22^FDVendor: {po_info.get('vendor', 'N/A')[:20]}^FS"
    #             label_zpl += f"^FO400,210^A0N,22,22^FDDate: {po_info.get('received_date', 'N/A')}^FS"
                
    #             # Large Quantity emphasis
    #             label_zpl += f"^FO400,250^A0N,20,20^FDQTY:^FS"
    #             label_zpl += f"^FO460,245^A0N,45,40^FD{qty_str}^FS"
    #         else:
    #             # CASE 2: GRADED/CHILD LOT
    #             proc_info = lot._get_processing_info() or {}
                
    #             # Right Side Info Block (X=400)
    #             label_zpl += f"^FO400,140^A0N,22,22^FDParent: {lot.parent_lot_id.name}^FS"
    #             label_zpl += f"^FO400,175^A0N,22,22^FDSorted: {proc_info.get('sorted_date', 'N/A')}^FS"
    #             label_zpl += f"^FO400,210^A0N,22,22^FDReport: {proc_info.get('sorting_report_name', 'N/A')[:18]}^FS"
                
    #             # Large Quantity emphasis
    #             label_zpl += f"^FO400,250^A0N,20,20^FDQTY:^FS"
    #             label_zpl += f"^FO460,245^A0N,45,40^FD{qty_str}^FS"

    #         # --- FOOTER SECTION ---
    #         # Dark Footer Bar (Professional look)
    #         label_zpl += "^FO50,340^GB712,45,45^FS"
    #         footer_text = "BULK RAW MATERIAL" if not lot.parent_lot_id else "QUALITY TESTED & GRADED"
    #         # Inverse text (White on Black)
    #         label_zpl += f"^FO50,352^A0N,28,28^FR^FB712,1,0,C,0^FD{footer_text}^FS"

    #         label_zpl += "^XZ\n"

    #         for _ in range(self.label_count):
    #             zpl_content += label_zpl

    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'custom_rsfp_module.print_zpl_action',
    #         'params': {'zpl_data': zpl_content}
    #     }

    # def action_generate_zpl(self):
    #     """Generate professional ZPL with balanced spacing for 100x50mm labels"""
    #     if not self.lot_ids:
    #         raise UserError(_("No lots selected for printing"))

    #     zpl_content = ""
        
    #     for lot in self.lot_ids:
    #         # Data Sanitation
    #         product_name = (lot.product_id.name or "").replace('^', '').replace('~', '')[:60]
    #         lot_name = lot.name or ""
    #         qty_str = f"{lot.product_qty} {lot.product_uom_id.name}"
            
    #         # Start Label (812x406 dots @ 203 DPI)
    #         label_zpl = "^XA^CI28^PW812^LL406^MTT^MD15"

    #         # --- TOP SECTION: PRODUCT IDENTIFICATION ---
    #         label_zpl += f"^FO50,30^A0N,35,35^FB712,2,0,L,0^FD{product_name}^FS"
            
    #         # Horizontal Divider
    #         label_zpl += "^FO50,110^GB712,3,3^FS"

    #         # --- MIDDLE SECTION: BARCODE LEFT, DETAILS RIGHT ---
    #         # 1. Barcode (Left Aligned at X=50)
    #         label_zpl += f"^FO50,150^BY2^BCN,100,N,N,N^FD{lot_name}^FS"
            
    #         # 2. Lot Number below Barcode (INCREASED SIZE & CLEARANCE)
    #         # Increased to 28,28 font; Width set to 350 to prevent collision with right side
    #         label_zpl += f"^FO50,265^A0N,28,28^FB350,1,0,C^FD{lot_name}^FS"

    #         # --- DYNAMIC DATA (SHIFTED FURTHER RIGHT TO X=440) ---
    #         if not lot.parent_lot_id:
    #             # CASE 1: BULK/RAW LOT
    #             po_info = lot._get_purchase_order_info() or {}
                
    #             label_zpl += f"^FO440,140^A0N,22,22^FDPO: {po_info.get('po_number', 'N/A')}^FS"
    #             label_zpl += f"^FO440,175^A0N,22,22^FDVendor: {po_info.get('vendor', 'N/A')[:20]}^FS"
    #             label_zpl += f"^FO440,210^A0N,22,22^FDDate: {po_info.get('received_date', 'N/A')}^FS"
                
    #             # Quantity emphasis
    #             label_zpl += f"^FO440,250^A0N,20,20^FDQTY:^FS"
    #             label_zpl += f"^FO500,245^A0N,45,40^FD{qty_str}^FS"
    #         else:
    #             # CASE 2: GRADED/CHILD LOT
    #             proc_info = lot._get_processing_info() or {}
                
    #             label_zpl += f"^FO440,140^A0N,22,22^FDParent: {lot.parent_lot_id.name}^FS"
    #             label_zpl += f"^FO440,175^A0N,22,22^FDSorted: {proc_info.get('sorted_date', 'N/A')}^FS"
    #             label_zpl += f"^FO440,210^A0N,22,22^FDReport: {proc_info.get('sorting_report_name', 'N/A')[:18]}^FS"
                
    #             # Quantity emphasis
    #             label_zpl += f"^FO440,250^A0N,20,20^FDQTY:^FS"
    #             label_zpl += f"^FO500,245^A0N,45,40^FD{qty_str}^FS"

    #         # --- FOOTER SECTION ---
    #         label_zpl += "^FO50,340^GB712,45,45^FS"
    #         footer_text = "BULK RAW MATERIAL" if not lot.parent_lot_id else "QUALITY TESTED & GRADED"
    #         label_zpl += f"^FO50,352^A0N,28,28^FR^FB712,1,0,C,0^FD{footer_text}^FS"

    #         label_zpl += "^XZ\n"

    #         for _ in range(self.label_count):
    #             zpl_content += label_zpl

    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'custom_rsfp_module.print_zpl_action',
    #         'params': {'zpl_data': zpl_content}
    #     }

    # def action_generate_zpl(self):
    #     """Generate professional ZPL with maximum clearance between barcode and data"""
    #     if not self.lot_ids:
    #         raise UserError(_("No lots selected for printing"))

    #     zpl_content = ""
        
    #     for lot in self.lot_ids:
    #         # Data Sanitation
    #         product_name = (lot.product_id.name or "").replace('^', '').replace('~', '')[:60]
    #         lot_name = lot.name or ""
    #         qty_str = f"{lot.product_qty} {lot.product_uom_id.name}"
            
    #         # Start Label (812x406 dots @ 203 DPI)
    #         label_zpl = "^XA^CI28^PW812^LL406^MTT^MD15"

    #         # --- TOP SECTION: PRODUCT IDENTIFICATION ---
    #         label_zpl += f"^FO50,30^A0N,35,35^FB712,2,0,L,0^FD{product_name}^FS"
            
    #         # Horizontal Divider
    #         label_zpl += "^FO50,110^GB712,3,3^FS"

    #         # --- MIDDLE SECTION: BARCODE LEFT, DETAILS RIGHT ---
    #         # 1. Barcode (Left Aligned at X=50)
    #         label_zpl += f"^FO50,150^BY2^BCN,100,N,N,N^FD{lot_name}^FS"
            
    #         # 2. Lot Number below Barcode
    #         label_zpl += f"^FO50,265^A0N,28,28^FB350,1,0,C^FD{lot_name}^FS"

    #         # --- DYNAMIC DATA (SHIFTED FURTHER RIGHT TO X=480 TO PREVENT COLLISION) ---
    #         if not lot.parent_lot_id:
    #             # CASE 1: BULK/RAW LOT
    #             po_info = lot._get_purchase_order_info() or {}
                
    #             label_zpl += f"^FO480,140^A0N,22,22^FDPO: {po_info.get('po_number', 'N/A')}^FS"
    #             label_zpl += f"^FO480,175^A0N,22,22^FDVendor: {po_info.get('vendor', 'N/A')[:18]}^FS"
    #             label_zpl += f"^FO480,210^A0N,22,22^FDDate: {po_info.get('received_date', 'N/A')}^FS"
                
    #             # Quantity emphasis (Aligned to the new X=480 start)
    #             label_zpl += f"^FO480,250^A0N,20,20^FDQTY:^FS"
    #             label_zpl += f"^FO540,245^A0N,45,40^FD{qty_str}^FS"
    #         else:
    #             # CASE 2: GRADED/CHILD LOT
    #             proc_info = lot._get_processing_info() or {}
                
    #             label_zpl += f"^FO480,140^A0N,22,22^FDParent: {lot.parent_lot_id.name}^FS"
    #             label_zpl += f"^FO480,175^A0N,22,22^FDSorted: {proc_info.get('sorted_date', 'N/A')}^FS"
    #             label_zpl += f"^FO480,210^A0N,22,22^FDReport: {proc_info.get('sorting_report_name', 'N/A')[:16]}^FS"
                
    #             # Quantity emphasis (Aligned to the new X=480 start)
    #             label_zpl += f"^FO480,250^A0N,20,20^FDQTY:^FS"
    #             label_zpl += f"^FO540,245^A0N,45,40^FD{qty_str}^FS"

    #         # --- FOOTER SECTION ---
    #         label_zpl += "^FO50,340^GB712,45,45^FS"
    #         footer_text = "BULK RAW MATERIAL" if not lot.parent_lot_id else "QUALITY TESTED & GRADED"
    #         label_zpl += f"^FO50,352^A0N,28,28^FR^FB712,1,0,C,0^FD{footer_text}^FS"

    #         label_zpl += "^XZ\n"

    #         for _ in range(self.label_count):
    #             zpl_content += label_zpl

    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'custom_rsfp_module.print_zpl_action',
    #         'params': {'zpl_data': zpl_content}
    #     }


    # def action_generate_zpl(self):
    #     """Professional ZPL: Centered Barcode on top, two columns below"""
    #     if not self.lot_ids:
    #         raise UserError(_("No lots selected for printing"))

    #     zpl_content = ""
    #     LABEL_WIDTH = 812  # Total dots for 4-inch label at 203 DPI

    #     for lot in self.lot_ids:
    #         # Data Sanitation
    #         product_name = (lot.product_id.name or "").replace('^', '').replace('~', '')[:60]
    #         lot_name = (lot.name or "").replace('^', '').replace('~', '')
    #         qty_str = f"{lot.product_qty} {lot.product_uom_id.name}"
            
    #         # --- DYNAMIC BARCODE CENTERING CALCULATION ---
    #         # Code 128 formula: (Chars * 11 modules + 35 modules overhead) * NarrowBarWidth
    #         # With ^BY2: (len * 22) + 70 dots
    #         barcode_width = (len(lot_name) * 22) + 70
    #         barcode_x = max(0, (LABEL_WIDTH - barcode_width) // 2)

    #         # Start Label & Speed/Darkness Config
    #         label_zpl = f"^XA^CI28^PW{LABEL_WIDTH}^LL406^PR2,2,2^MD15"

    #         # --- SECTION 1: CENTERED BARCODE (TOP) ---
    #         label_zpl += f"^FO{barcode_x},30^BY2^BCN,100,N,N,N^FD{lot_name}^FS"
            
    #         # Horizontal Divider
    #         label_zpl += "^FO50,170^GB712,3,3^FS"

    #         # --- SECTION 2: TWO-COLUMN DETAILS ---
    #         # COLUMN 1 (Left) - X=50
    #         label_zpl += f"^FO50,190^A0N,25,25^FB350,2,0,L,0^FDProd: {product_name}^FS"
    #         label_zpl += f"^FO50,260^A0N,25,25^FDLot: {lot_name}^FS"
    #         label_zpl += f"^FO50,295^A0N,35,35^FDQTY: {qty_str}^FS"

    #         # COLUMN 2 (Right) - X=450
    #         if not lot.parent_lot_id:
    #             po_info = lot._get_purchase_order_info() or {}
    #             label_zpl += f"^FO450,190^A0N,22,22^FDPO: {po_info.get('po_number', 'N/A')}^FS"
    #             label_zpl += f"^FO450,225^A0N,22,22^FDVendor: {po_info.get('vendor', 'N/A')[:18]}^FS"
    #             label_zpl += f"^FO450,260^A0N,22,22^FDDate: {po_info.get('received_date', 'N/A')}^FS"
    #         else:
    #             proc_info = lot._get_processing_info() or {}
    #             label_zpl += f"^FO450,190^A0N,22,22^FDParent: {lot.parent_lot_id.name}^FS"
    #             label_zpl += f"^FO450,225^A0N,22,22^FDSorted: {proc_info.get('sorted_date', 'N/A')}^FS"
    #             label_zpl += f"^FO450,260^A0N,22,22^FDReport: {proc_info.get('sorting_report_name', 'N/A')[:16]}^FS"

    #         # --- FOOTER ---
    #         label_zpl += "^FO50,340^GB712,45,45^FS"
    #         footer_text = "BULK RAW MATERIAL" if not lot.parent_lot_id else "QUALITY TESTED & GRADED"
    #         label_zpl += f"^FO50,352^A0N,28,28^FR^FB712,1,0,C,0^FD{footer_text}^FS"

    #         label_zpl += "^XZ\n"

    #         for _ in range(self.label_count):
    #             zpl_content += label_zpl

    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'custom_rsfp_module.print_zpl_action',
    #         'params': {'zpl_data': zpl_content}
    #     }


    # def action_generate_zpl(self):
    #     """Professional ZPL: Centered Barcode, Consistent Fonts, Reliable Footer"""
    #     if not self.lot_ids:
    #         raise UserError(_("No lots selected for printing"))

    #     zpl_content = ""
    #     LABEL_WIDTH = 812  # 4-inch label @ 203 DPI

    #     for lot in self.lot_ids:
    #         # Data Sanitation
    #         product_name = (lot.product_id.name or "").replace('^', '').replace('~', '')[:60]
    #         lot_name = (lot.name or "").replace('^', '').replace('~', '')
    #         qty_str = f"{lot.product_qty} {lot.product_uom_id.name}"
            
    #         # --- BARCODE CALCULATION ---
    #         # With ^BY2: (len * 22) + 70 dots
    #         barcode_width = (len(lot_name) * 22) + 70
    #         barcode_x = max(0, (LABEL_WIDTH - barcode_width) // 2)

    #         # Start Label: Speed 2, Darkness 15
    #         label_zpl = f"^XA^CI28^PW{LABEL_WIDTH}^LL406^PR2,2,2^MD15"

    #         # --- SECTION 1: CENTERED BARCODE (TOP) ---
    #         # High-quality barcode without human-readable text
    #         label_zpl += f"^FO{barcode_x},40^BY2^BCN,100,N,N,N^FD{lot_name}^FS"
            
    #         # Upper Divider
    #         label_zpl += "^FO50,165^GB712,2,2^FS"

    #         # --- SECTION 2: CONSISTENT TWO-COLUMN DATA ---
    #         # Uniform Font Size (24,24) used for all professional detail metrics
    #         FONT_SIZE = "24,24"

    #         # COLUMN 1 (Left) - X=50
    #         label_zpl += f"^FO50,190^A0N,{FONT_SIZE}^FB370,2,0,L,0^FDProduct: {product_name}^FS"
    #         label_zpl += f"^FO50,255^A0N,{FONT_SIZE}^FDLot No: {lot_name}^FS"
    #         label_zpl += f"^FO50,290^A0N,{FONT_SIZE}^FDQuantity: {qty_str}^FS"

    #         # COLUMN 2 (Right) - X=450
    #         if not lot.parent_lot_id:
    #             po_info = lot._get_purchase_order_info() or {}
    #             label_zpl += f"^FO450,190^A0N,{FONT_SIZE}^FDPO: {po_info.get('po_number', 'N/A')}^FS"
    #             label_zpl += f"^FO450,225^A0N,{FONT_SIZE}^FDVendor: {po_info.get('vendor', 'N/A')[:16]}^FS"
    #             label_zpl += f"^FO450,260^A0N,{FONT_SIZE}^FDDate: {po_info.get('received_date', 'N/A')}^FS"
    #         else:
    #             proc_info = lot._get_processing_info() or {}
    #             label_zpl += f"^FO450,190^A0N,{FONT_SIZE}^FDParent: {lot.parent_lot_id.name}^FS"
    #             label_zpl += f"^FO450,225^A0N,{FONT_SIZE}^FDSorted: {proc_info.get('sorted_date', 'N/A')}^FS"
    #             label_zpl += f"^FO450,260^A0N,{FONT_SIZE}^FDReport: {proc_info.get('sorting_report_name', 'N/A')[:14]}^FS"

    #         # --- SECTION 3: MINIMALISTIC FOOTER ---
    #         # Replacing the solid block with a thin line and centered text for better print reliability
    #         label_zpl += "^FO50,340^GB712,2,2^FS"
    #         footer_text = "--- BULK RAW MATERIAL ---" if not lot.parent_lot_id else "--- QUALITY TESTED & GRADED ---"
    #         label_zpl += f"^FO50,355^A0N,26,26^FB712,1,0,C,0^FD{footer_text}^FS"

    #         label_zpl += "^XZ\n"

    #         for _ in range(self.label_count):
    #             zpl_content += label_zpl

    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'custom_rsfp_module.print_zpl_action',
    #         'params': {'zpl_data': zpl_content}
    #     }

    # def action_generate_zpl(self):
    #     """Minimalist ZPL: Reduced Barcode, No Lines, Consistent Spacing"""
    #     if not self.lot_ids:
    #         raise UserError(_("No lots selected for printing"))

    #     zpl_content = ""
    #     LABEL_WIDTH = 812  # 4-inch label @ 203 DPI

    #     for lot in self.lot_ids:
    #         # Data Sanitation
    #         product_name = (lot.product_id.name or "").replace('^', '').replace('~', '')[:60]
    #         lot_name = (lot.name or "").replace('^', '').replace('~', '')
    #         qty_str = f"{lot.product_qty} {lot.product_uom_id.name}"
            
    #         # --- REDUCED BARCODE CALCULATION ---
    #         # Narrow bar width reduced to 2, height reduced to 80 dots
    #         barcode_width = (len(lot_name) * 22) + 70
    #         barcode_x = max(0, (LABEL_WIDTH - barcode_width) // 2)

    #         # Start Label: Speed 2, Darkness 15
    #         label_zpl = f"^XA^CI28^PW{LABEL_WIDTH}^LL406^PR2,2,2^MD15"

    #         # --- SECTION 1: CENTERED BARCODE (TOP) ---
    #         # Height reduced from 100 to 80 for a subtler look
    #         label_zpl += f"^FO{barcode_x},50^BY2^BCN,80,N,N,N^FD{lot_name}^FS"
            
    #         # --- SECTION 2: CONSISTENT TWO-COLUMN DATA ---
    #         # Standardized Font Size
    #         FONT_SIZE = "24,24"

    #         # COLUMN 1 (Left) - X=50
    #         label_zpl += f"^FO50,170^A0N,{FONT_SIZE}^FB370,2,0,L,0^FDProduct: {product_name}^FS"
    #         label_zpl += f"^FO50,230^A0N,{FONT_SIZE}^FDLot No: {lot_name}^FS"
    #         label_zpl += f"^FO50,265^A0N,{FONT_SIZE}^FDQuantity: {qty_str}^FS"

    #         # COLUMN 2 (Right) - X=450
    #         if not lot.parent_lot_id:
    #             po_info = lot._get_purchase_order_info() or {}
    #             label_zpl += f"^FO450,170^A0N,{FONT_SIZE}^FDPO: {po_info.get('po_number', 'N/A')}^FS"
    #             label_zpl += f"^FO450,205^A0N,{FONT_SIZE}^FDVendor: {po_info.get('vendor', 'N/A')[:16]}^FS"
    #             label_zpl += f"^FO450,240^A0N,{FONT_SIZE}^FDDate: {po_info.get('received_date', 'N/A')}^FS"
    #         else:
    #             proc_info = lot._get_processing_info() or {}
    #             label_zpl += f"^FO450,170^A0N,{FONT_SIZE}^FDParent: {lot.parent_lot_id.name}^FS"
    #             label_zpl += f"^FO450,205^A0N,{FONT_SIZE}^FDSorted: {proc_info.get('sorted_date', 'N/A')}^FS"
    #             label_zpl += f"^FO450,240^A0N,{FONT_SIZE}^FDReport: {proc_info.get('sorting_report_name', 'N/A')[:14]}^FS"

    #         # --- SECTION 3: SIMPLE TEXT FOOTER ---
    #         # No lines, just clean centered text at the bottom
    #         footer_text = lot.parent_lot_id and "QUALITY TESTED & GRADED" or "BULK RAW MATERIAL"
    #         label_zpl += f"^FO50,350^A0N,24,24^FB712,1,0,C,0^FD{footer_text}^FS"

    #         label_zpl += "^XZ\n"

    #         for _ in range(self.label_count):
    #             zpl_content += label_zpl

    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'custom_rsfp_module.print_zpl_action',
    #         'params': {'zpl_data': zpl_content}
    #     }

    # def action_generate_zpl(self):
    #     """Minimalist ZPL: Optimized Column Widths (Left Heavy for Variable Data)"""
    #     if not self.lot_ids:
    #         raise UserError(_("No lots selected for printing"))

    #     zpl_content = ""
    #     LABEL_WIDTH = 812  # 4-inch label @ 203 DPI

    #     for lot in self.lot_ids:
    #         # Data Sanitation
    #         product_name = (lot.product_id.name or "").replace('^', '').replace('~', '')[:60]
    #         lot_name = (lot.name or "").replace('^', '').replace('~', '')
    #         qty_str = f"{lot.product_qty} {lot.product_uom_id.name}"
            
    #         # --- BARCODE CALCULATION ---
    #         barcode_width = (len(lot_name) * 22) + 70
    #         barcode_x = max(0, (LABEL_WIDTH - barcode_width) // 2)

    #         # Start Label
    #         label_zpl = f"^XA^CI28^PW{LABEL_WIDTH}^LL406^PR2,2,2^MD15"

    #         # --- SECTION 1: CENTERED BARCODE (TOP) ---
    #         label_zpl += f"^FO{barcode_x},50^BY2^BCN,80,N,N,N^FD{lot_name}^FS"
            
    #         # --- SECTION 2: OPTIMIZED TWO-COLUMN DATA ---
    #         FONT_SIZE = "24,24"
    #         LEFT_X = 50
    #         LEFT_WIDTH = 480  # Increased width for long vendor/lot strings
    #         RIGHT_X = 550     # Shifted right to accommodate the larger left column
    #         RIGHT_WIDTH = 230 # Smaller width for shorter strings

    #         if not lot.parent_lot_id:
    #             # CASE: BULK RAW MATERIAL
    #             po_info = lot._get_purchase_order_info() or {}
                
    #             # Left Column: Product, Lot, Vendor (Space Intensive)
    #             label_zpl += f"^FO{LEFT_X},170^A0N,{FONT_SIZE}^FB{LEFT_WIDTH},2,0,L,0^FDProduct: {product_name}^FS"
    #             label_zpl += f"^FO{LEFT_X},230^A0N,{FONT_SIZE}^FB{LEFT_WIDTH},1,0,L,0^FDLot No: {lot_name}^FS"
    #             label_zpl += f"^FO{LEFT_X},265^A0N,{FONT_SIZE}^FB{LEFT_WIDTH},1,0,L,0^FDVendor: {po_info.get('vendor', 'N/A')[:30]}^FS"
                
    #             # Right Column: Qty, PO, Date (Fixed/Short)
    #             label_zpl += f"^FO{RIGHT_X},170^A0N,{FONT_SIZE}^FB{RIGHT_WIDTH},1,0,L,0^FDQty: {qty_str}^FS"
    #             label_zpl += f"^FO{RIGHT_X},205^A0N,{FONT_SIZE}^FB{RIGHT_WIDTH},1,0,L,0^FDPO: {po_info.get('po_number', 'N/A')}^FS"
    #             label_zpl += f"^FO{RIGHT_X},240^A0N,{FONT_SIZE}^FB{RIGHT_WIDTH},1,0,L,0^FDDate: {po_info.get('received_date', 'N/A')}^FS"
    #         else:
    #             # CASE: GRADED PRODUCT
    #             proc_info = lot._get_processing_info() or {}
                
    #             # Left Column: Product, Lot, Parent (Space Intensive)
    #             label_zpl += f"^FO{LEFT_X},170^A0N,{FONT_SIZE}^FB{LEFT_WIDTH},2,0,L,0^FDProduct: {product_name}^FS"
    #             label_zpl += f"^FO{LEFT_X},230^A0N,{FONT_SIZE}^FB{LEFT_WIDTH},1,0,L,0^FDLot No: {lot_name}^FS"
    #             label_zpl += f"^FO{LEFT_X},265^A0N,{FONT_SIZE}^FB{LEFT_WIDTH},1,0,L,0^FDParent: {lot.parent_lot_id.name}^FS"
                
    #             # Right Column: Qty, Sorted Date, Report (Fixed/Short)
    #             label_zpl += f"^FO{RIGHT_X},170^A0N,{FONT_SIZE}^FB{RIGHT_WIDTH},1,0,L,0^FDQty: {qty_str}^FS"
    #             label_zpl += f"^FO{RIGHT_X},205^A0N,{FONT_SIZE}^FB{RIGHT_WIDTH},1,0,L,0^FDSorted: {proc_info.get('sorted_date', 'N/A')}^FS"
    #             label_zpl += f"^FO{RIGHT_X},240^A0N,{FONT_SIZE}^FB{RIGHT_WIDTH},1,0,L,0^FDReport: {proc_info.get('sorting_report_name', 'N/A')[:14]}^FS"

    #         # --- SECTION 3: FOOTER ---
    #         footer_text = lot.parent_lot_id and "QUALITY TESTED & GRADED" or "BULK RAW MATERIAL"
    #         label_zpl += f"^FO50,350^A0N,24,24^FB712,1,0,C,0^FD{footer_text}^FS"

    #         label_zpl += "^XZ\n"

    #         for _ in range(self.label_count):
    #             zpl_content += label_zpl

    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'custom_rsfp_module.print_zpl_action',
    #         'params': {'zpl_data': zpl_content}
    #     }

    def action_generate_zpl(self):
        """Shifted Upwards ZPL: Strictly 100mm x 50mm (812x406 Dots)"""
        if not self.lot_ids:
            raise UserError(_("No lots selected for printing"))

        zpl_content = ""
        LABEL_WIDTH = 812  # 100mm @ 203 DPI
        LABEL_HEIGHT = 406 # 50mm @ 203 DPI

        for lot in self.lot_ids:
            # Data Sanitation
            product_name = (lot.product_id.name or "").replace('^', '').replace('~', '')[:60]
            lot_name = (lot.name or "").replace('^', '').replace('~', '')
            qty_str = f"{lot.product_qty} {lot.product_uom_id.name}"
            
            # --- BARCODE CALCULATION ---
            barcode_width = (len(lot_name) * 22) + 70
            barcode_x = max(0, (LABEL_WIDTH - barcode_width) // 2)

            # Start Label - Explicitly setting LL406 for 50mm height
            label_zpl = f"^XA^CI28^PW{LABEL_WIDTH}^LL{LABEL_HEIGHT}^PR2,2,2^MD15"

            # --- SECTION 1: CENTERED BARCODE (SHIFTED UP TO Y=20) ---
            label_zpl += f"^FO{barcode_x},20^BY2^BCN,70,N,N,N^FD{lot_name}^FS"
            
            # --- SECTION 2: DATA COLUMNS (SHIFTED UP) ---
            FONT_SIZE = "24,24"
            LEFT_X = 50
            LEFT_WIDTH = 480
            RIGHT_X = 550
            RIGHT_WIDTH = 230

            # Base Y for Section 2 (Shifted from 170 down to 110)
            BASE_Y = 110 

            if not lot.parent_lot_id:
                # CASE: BULK RAW MATERIAL
                po_info = lot._get_purchase_order_info() or {}
                
                label_zpl += f"^FO{LEFT_X},{BASE_Y}^A0N,{FONT_SIZE}^FB{LEFT_WIDTH},2,0,L,0^FDProduct: {product_name}^FS"
                label_zpl += f"^FO{LEFT_X},{BASE_Y+60}^A0N,{FONT_SIZE}^FB{LEFT_WIDTH},1,0,L,0^FDLot No: {lot_name}^FS"
                label_zpl += f"^FO{LEFT_X},{BASE_Y+95}^A0N,{FONT_SIZE}^FB{LEFT_WIDTH},1,0,L,0^FDVendor: {po_info.get('vendor', 'N/A')[:30]}^FS"
                
                label_zpl += f"^FO{RIGHT_X},{BASE_Y}^A0N,{FONT_SIZE}^FB{RIGHT_WIDTH},1,0,L,0^FDQty: {qty_str}^FS"
                label_zpl += f"^FO{RIGHT_X},{BASE_Y+35}^A0N,{FONT_SIZE}^FB{RIGHT_WIDTH},1,0,L,0^FDPO: {po_info.get('po_number', 'N/A')}^FS"
                label_zpl += f"^FO{RIGHT_X},{BASE_Y+70}^A0N,{FONT_SIZE}^FB{RIGHT_WIDTH},1,0,L,0^FDDate: {po_info.get('received_date', 'N/A')}^FS"
            else:
                # CASE: GRADED PRODUCT
                proc_info = lot._get_processing_info() or {}
                
                label_zpl += f"^FO{LEFT_X},{BASE_Y}^A0N,{FONT_SIZE}^FB{LEFT_WIDTH},2,0,L,0^FDProduct: {product_name}^FS"
                label_zpl += f"^FO{LEFT_X},{BASE_Y+60}^A0N,{FONT_SIZE}^FB{LEFT_WIDTH},1,0,L,0^FDLot No: {lot_name}^FS"
                label_zpl += f"^FO{LEFT_X},{BASE_Y+95}^A0N,{FONT_SIZE}^FB{LEFT_WIDTH},1,0,L,0^FDParent: {lot.parent_lot_id.name}^FS"
                
                label_zpl += f"^FO{RIGHT_X},{BASE_Y}^A0N,{FONT_SIZE}^FB{RIGHT_WIDTH},1,0,L,0^FDQty: {qty_str}^FS"
                label_zpl += f"^FO{RIGHT_X},{BASE_Y+35}^A0N,{FONT_SIZE}^FB{RIGHT_WIDTH},1,0,L,0^FDSorted: {proc_info.get('sorted_date', 'N/A')}^FS"
                label_zpl += f"^FO{RIGHT_X},{BASE_Y+70}^A0N,{FONT_SIZE}^FB{RIGHT_WIDTH},1,0,L,0^FDReport: {proc_info.get('sorting_report_name', 'N/A')[:14]}^FS"

            # --- SECTION 3: FOOTER (SHIFTED FROM 350 TO 250) ---
            footer_text = lot.parent_lot_id and "QUALITY TESTED & GRADED" or "BULK RAW MATERIAL"
            label_zpl += f"^FO50,250^A0N,24,24^FB712,1,0,C,0^FD{footer_text}^FS"

            label_zpl += "^XZ\n"

            for _ in range(self.label_count):
                zpl_content += label_zpl

        return {
            'type': 'ir.actions.client',
            'tag': 'custom_rsfp_module.print_zpl_action',
            'params': {'zpl_data': zpl_content}
        }





