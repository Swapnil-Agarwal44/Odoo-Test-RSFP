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

    # Arrived quantity field - captures initial quantity when lot was created
    arrived_quantity = fields.Float(
        string='Arrived Quantity',
        readonly=True,
        digits='Product Unit of Measure',
        help="Initial quantity when the lot was first created/received - remains constant",
        copy=False
    )

    @api.model
    def create(self, vals):
        """Override create to inject custom lot name and set initial arrived_quantity"""
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
                
        # Create the lot first
        lot = super(StockLot, self).create(vals)

        # Ensure we have a valid lot record
        if not lot:
            _logger.error("Super create returned None - this should not happen!")
            raise ValueError("Failed to create lot record")
        
        # Set initial arrived_quantity based on context or initial quantity
        try:
            initial_qty = self._get_initial_quantity_for_lot(lot, vals)
            if initial_qty > 0 and not lot.arrived_quantity:
                lot.sudo().write({'arrived_quantity': initial_qty})
                _logger.info(f"Set arrived_quantity to {initial_qty} for lot {lot.name}")
        except Exception as e:
            _logger.warning(f"Could not set arrived_quantity for lot {lot.name}: {e}")
        
        # ALWAYS return the lot record
        return lot
    
    def _get_initial_quantity_for_lot(self, lot, vals):
        """Determine the initial quantity for a newly created lot"""
        _logger.info(f"=== Getting initial quantity for lot: {lot.name} ===")
        
        # 1. Check if quantity specified in context (for child lots)
        context_qty = self._context.get('arrived_quantity') or self._context.get('initial_quantity')
        if context_qty and context_qty > 0:
            _logger.info(f"Found quantity in context: {context_qty}")
            return context_qty
        
        # 2. Check current product_qty (for immediate stock creation scenarios)
        if lot.product_qty > 0:
            _logger.info(f"Using current product_qty: {lot.product_qty}")
            return lot.product_qty
        
        # For manual creation without immediate stock, return 0
        # The quantity will be set when the first stock move is processed
        _logger.info("No initial quantity found, will be set on first stock move")
        return 0.0
    
    def _set_arrived_quantity_if_needed(self, quantity):
        """Set arrived_quantity if not already set and this is the first quantity assignment"""
        self.ensure_one()
        if not self.arrived_quantity and quantity > 0:
            # Use sudo to ensure we can write even if the field is readonly
            self.sudo().write({'arrived_quantity': quantity})
            _logger.info(f"Auto-set arrived_quantity to {quantity} for lot {self.name}")
            return True
        elif self.arrived_quantity:
            _logger.debug(f"Lot {self.name} already has arrived_quantity set to {self.arrived_quantity}")
        return False
    
    @api.model
    def _migrate_existing_lots_arrived_quantity(self):
        """Migration method to set arrived_quantity for existing lots"""
        _logger.info("=== MIGRATING EXISTING LOTS ===")
        
        # Find all lots without arrived_quantity
        lots_without_arrived_qty = self.search([
            ('arrived_quantity', '=', 0),
            ('product_qty', '>', 0)
        ])
        
        _logger.info(f"Found {len(lots_without_arrived_qty)} lots without arrived_quantity")
        
        for lot in lots_without_arrived_qty:
            try:
                # For existing lots, use current product_qty as arrived_quantity
                # This represents the best available data for existing lots
                lot.sudo().write({'arrived_quantity': lot.product_qty})
                _logger.info(f"Migrated lot {lot.name}: set arrived_quantity to {lot.product_qty}")
            except Exception as e:
                _logger.error(f"Failed to migrate lot {lot.name}: {e}")
        
        _logger.info("=== MIGRATION COMPLETE ===")
    
    def action_manual_migration(self):
        """Manual action to run migration for existing lots (can be called from UI)"""
        self._migrate_existing_lots_arrived_quantity()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Migration Complete',
                'message': 'Arrived quantity has been updated for existing lots.',
                'type': 'success',
                'sticky': False,
            }
        }
    
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

        try:
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
                return f"{abbreviation}-{date_str}-ERROR"  # Return something rather than None
            
            # Format: ABBR-DDMMYY-XXXX (e.g., ABC-161025-0001)
            lot_name = f"{abbreviation}-{date_str}-{seq_number}"
            _logger.info(f"Final lot name: {lot_name}")
            return lot_name
            
        except Exception as e:
            _logger.error(f"Error generating lot name: {e}")
            return f"ERR-{fields.Date.today().strftime('%d%m%y')}-001"  # Fallback name
    
    

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
            'tested_date': 'N/A',
            'sorting_report_name': 'N/A',  
        }
        
        # Get sorting information
        sorting_report = self.env['custom.sorting.report'].search([
            ('parent_lot_id', '=', self.parent_lot_id.id),
            ('state', '=', 'confirmed')
        ], limit=1)
        
        if sorting_report:
            info['sorted_date'] = sorting_report.sorting_date.strftime('%d/%m/%Y') if sorting_report.sorting_date else 'N/A'
            info['sorting_report_name'] = sorting_report.name  # Set the report name
        
        # Get quality testing information
        quality_report = self.env['custom.quality.report'].search([
            ('child_lot_id', '=', self.id),
            ('state', '=', 'confirmed')
        ], limit=1)
        
        if quality_report:
            info['tested_date'] = quality_report.testing_date.strftime('%d/%m/%Y') if quality_report.testing_date else 'N/A'
        
        return info
    
    @api.model
    def action_set_arrived_quantity(self):
        """
        PLACEHOLDER: Defines the action mentioned in the traceback to allow XML validation.
        This method should handle setting the arrived_quantity field, perhaps via a wizard.
        For now, we define it to prevent the server error.
        """
        raise UserError("The method 'action_set_arrived_quantity' is called but not fully implemented yet.")
