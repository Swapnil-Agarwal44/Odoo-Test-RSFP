from odoo import fields, models, api # type: ignore
from odoo.exceptions import UserError # type: ignore
import logging

# This file is used to create a default customized lot/sequence name whenever the lot is created in the lot/sequence menu in the inventory tab
# This file complements the stock_move_line.py file
# The sequence will be generated if the product id is first selected in the form.  

_logger = logging.getLogger(__name__)

class StockLot(models.Model):
    _inherit = 'stock.lot'
    _description = 'Stock Lot Extension'

    # Make the ref field clickable and add parent lot reference
    parent_lot_id = fields.Many2one(
        'stock.lot',
        string='Parent Lot',
        readonly=True,
        help="The parent lot from which this child lot was created during quality grading"
    )

    @api.model
    def create(self, vals):
        """Override create to inject custom lot name if not provided"""
        _logger.info("=== LOT CREATE METHOD CALLED ===")
        _logger.info(f"Values: {vals}")
        _logger.info(f"Context: {self._context}")
        
        # Check if name is not provided or is a placeholder/default value
        should_generate = (
            not vals.get('name') or 
            vals.get('name', '').isdigit() or
            vals.get('name', '').startswith('LOT/') or
            vals.get('name', '') == ''
        )
        
        _logger.info(f"Should generate custom name: {should_generate}")
        
        if should_generate:
            # Try to get product_id from vals or context
            product_id = vals.get('product_id') or self._context.get('default_product_id') or self._context.get('product_id')
            _logger.info(f"Product ID: {product_id}")
            
            if product_id:
                custom_name = self._generate_lot_name(product_id)
                _logger.info(f"Generated custom name: {custom_name}")
                if custom_name:
                    vals['name'] = custom_name
                    _logger.info(f"Name set to: {vals['name']}")
        
        _logger.info(f"Final vals before super: {vals}")
        return super(StockLot, self).create(vals)
    
    def action_view_parent_lot(self):
        """Action to view the parent lot"""
        self.ensure_one()
        if not self.parent_lot_id:
            raise UserError("This lot does not have a parent lot.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Parent Lot',
            'res_model': 'stock.lot',
            'res_id': self.parent_lot_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def default_get(self, fields_list):
        """Override to provide custom default lot name"""
        _logger.info("=== LOT DEFAULT_GET CALLED ===")
        _logger.info(f"Context: {self._context}")
        
        res = super(StockLot, self).default_get(fields_list)
        _logger.info(f"Super result: {res}")
        
        # Only generate if 'name' is in the requested fields
        if 'name' in fields_list:
            product_id = self._context.get('default_product_id') or self._context.get('product_id')
            _logger.info(f"Product ID from context: {product_id}")
            
            if product_id:
                custom_name = self._generate_lot_name(product_id)
                _logger.info(f"Generated custom name: {custom_name}")
                if custom_name:
                    res['name'] = custom_name
            else:
                _logger.info("No product_id in context - will be set via onchange")
        
        _logger.info(f"Final result: {res}")
        return res

    @api.model
    def _generate_lot_name(self, product_id):
        """Generate lot name with format: ABBR-DDMMYY-XXXX"""
        _logger.info(f"=== GENERATE_LOT_NAME called with product_id: {product_id} ===")
        
        if not product_id:
            _logger.info("No product_id provided")
            return False
            
        product = self.env['product.product'].browse(product_id)
        if not product.exists():
            _logger.info("Product does not exist")
            return False
        
        _logger.info(f"Product found: {product.name}")
        abbreviation = product.product_tmpl_id.lot_abbreviation or 'XX'
        _logger.info(f"Abbreviation: {abbreviation}")
        
        today = fields.Date.today()
        date_str = today.strftime('%d%m%y')
        _logger.info(f"Date string: {date_str}")
        
        # Get the next sequence number for today
        sequence_code = 'parent.lot.daily.sequence'
        seq_number = self.env['ir.sequence'].next_by_code(sequence_code)
        _logger.info(f"Sequence number: {seq_number}")
        
        if not seq_number:
            _logger.error("Sequence not found!")
            return f"{abbreviation}-{date_str}-ERROR"
        
        # Format: ABBR-DDMMYY-XXXX (e.g., ABC-161025-0001)
        lot_name = f"{abbreviation}-{date_str}-{seq_number}"
        _logger.info(f"Final lot name: {lot_name}")
        return lot_name

    @api.onchange('product_id')
    def _onchange_product_id_generate_lot(self):
        """Generate lot name when product is selected"""
        _logger.info(f"=== LOT ONCHANGE TRIGGERED === Product: {self.product_id.name if self.product_id else 'None'}")
        _logger.info(f"Current name: {self.name}")
        
        if self.product_id:
            # Check if current name is the default Odoo sequence (starts with numbers)
            # or is empty/placeholder
            should_replace = (
                not self.name or 
                self.name.isdigit() or  # Pure numbers like "0000014"
                self.name.startswith('LOT/') or  # Default LOT sequence
                self.name == ''
            )
            
            _logger.info(f"Should replace name: {should_replace}")
            
            if should_replace:
                generated_name = self._generate_lot_name(self.product_id.id)
                _logger.info(f"Generated name: {generated_name}")
                if generated_name:
                    self.name = generated_name
                    _logger.info(f"Name updated to: {self.name}")

    def _get_purchase_order_info(self):
        """Get purchase order information for parent lots"""
        self.ensure_one()
        
        # Search for purchase order through stock moves  
        move_lines = self.env['stock.move.line'].search([
            ('lot_id', '=', self.id),
            ('state', '=', 'done'),
            ('move_id.purchase_line_id', '!=', False)
        ], limit=1)
        
        if move_lines and move_lines.move_id.purchase_line_id:
            po_line = move_lines.move_id.purchase_line_id
            po = po_line.order_id
            
            # Get received date from picking
            received_date = 'N/A'
            if move_lines.picking_id and move_lines.picking_id.date_done:
                received_date = move_lines.picking_id.date_done.strftime('%d/%m/%Y')
            
            return {
                'po_number': po.name,
                'vendor': po.partner_id.name,
                'order_date': po.date_order.strftime('%d/%m/%Y') if po.date_order else 'N/A',
                'received_date': received_date,
                'original_qty': po_line.product_qty,
                'uom': po_line.product_uom.name,
            }
        return {}
    
    def _get_processing_info(self):
        """Get processing information for child lots"""
        self.ensure_one()
        
        if not self.parent_lot_id:
            return {}
        
        info = {
            'sorted_date': 'N/A',
            'tested_date': 'N/A'
        }
        
        # Get sorting information
        sorting_report = self.env['custom.sorting.report'].search([
            ('parent_lot_id', '=', self.parent_lot_id.id),
            ('state', '=', 'confirmed')
        ], limit=1)
        
        if sorting_report:
            info['sorted_date'] = sorting_report.sorting_date.strftime('%d/%m/%Y') if sorting_report.sorting_date else 'N/A'
        
        # Get quality testing information
        quality_report = self.env['custom.quality.report'].search([
            ('child_lot_id', '=', self.id),
            ('state', '=', 'confirmed')
        ], limit=1)
        
        if quality_report:
            info['tested_date'] = quality_report.testing_date.strftime('%d/%m/%Y') if quality_report.testing_date else 'N/A'
        
        return info