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

    @api.model
    def create(self, vals):
        """Override create to inject custom lot name if not provided"""
        _logger.info("=== CREATE METHOD CALLED ===")
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

    @api.model
    def default_get(self, fields_list):
        """Override to provide custom default lot name"""
        _logger.info("=== DEFAULT_GET CALLED ===")
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
        _logger.info(f"=== ONCHANGE TRIGGERED === Product: {self.product_id.name if self.product_id else 'None'}")
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