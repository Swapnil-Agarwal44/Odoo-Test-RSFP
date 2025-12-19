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
    
    #function to send the label zpl code
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





