from odoo import fields, models, api # type: ignore
from odoo.exceptions import UserError # type: ignore
import logging

_logger = logging.getLogger(__name__)

class StockLot(models.Model):
    _inherit = 'stock.lot'
    _description = 'Stock Lot Extension'

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



# from odoo import fields, models, api # type: ignore
# from odoo.exceptions import UserError # type: ignore

# class StockLot(models.Model):
#     _inherit = 'stock.lot'
#     _description = 'Stock Lot Extension'

#     @api.model
#     def default_get(self, fields_list):
#         """Override to provide custom default lot name"""
#         res = super(StockLot, self).default_get(fields_list)
        
#         # Only generate if 'name' is in the requested fields
#         if 'name' in fields_list:
#             product_id = self._context.get('default_product_id') or self._context.get('product_id')
            
#             if product_id:
#                 custom_name = self._generate_lot_name(product_id)
#                 if custom_name:
#                     res['name'] = custom_name
        
#         return res

#     @api.model
#     def _generate_lot_name(self, product_id):
#         """Generate lot name with format: ABBR-DDMMYY-XXXX"""
#         if not product_id:
#             return False
            
#         product = self.env['product.product'].browse(product_id)
#         if not product.exists():
#             return False
            
#         abbreviation = product.product_tmpl_id.lot_abbreviation or 'XX'
        
#         today = fields.Date.today()
#         date_str = today.strftime('%d%m%y')
        
#         # Get the next sequence number for today
#         sequence_code = 'parent.lot.daily.sequence'
#         seq_number = self.env['ir.sequence'].next_by_code(sequence_code)
        
#         if not seq_number:
#             return f"{abbreviation}-{date_str}-ERROR"
        
#         # Format: ABBR-DDMMYY-XXXX (e.g., ABC-161025-0001)
#         lot_name = f"{abbreviation}-{date_str}-{seq_number}"
#         return lot_name

#     @api.onchange('product_id')
#     def _onchange_product_id_generate_lot(self):
#         """Generate lot name when product is selected"""
#         if self.product_id and not self.name:
#             generated_name = self._generate_lot_name(self.product_id.id)
#             if generated_name:
#                 self.name = generated_name




# from odoo import fields, models, api # type: ignore
# from odoo.exceptions import UserError # type: ignore

# class StockLot(models.Model):
#     _inherit = 'stock.lot'
#     _description = 'Stock Lot Extension'

#     # Override the name field to add our custom default
#     name = fields.Char(
#         'Lot/Serial Number',
#         default=lambda self: self._get_default_lot_name(),
#         required=True,
#         help="Unique Lot/Serial Number"
#     )

#     @api.model
#     def _get_default_lot_name(self):
#         """Generate default lot name with format: ABBR-DDMMYY-XXXX"""
#         # Try to get product_id from context
#         product_id = self._context.get('default_product_id') or self._context.get('product_id')
#         if not product_id:
#             # Return empty string if no product in context
#             # User will need to fill it manually or it will be set when product is selected
#             return ''
#         product = self.env['product.product'].browse(product_id)
#         if not product.exists():
#             return ''
#         abbreviation = product.product_tmpl_id.lot_abbreviation or 'XX'
#         today = fields.Date.today()
#         date_str = today.strftime('%d%m%y')
#         # Get the next sequence number for today
#         sequence_code = 'parent.lot.daily.sequence'
#         seq_number = self.env['ir.sequence'].next_by_code(sequence_code)
#         if not seq_number:
#             return f"{abbreviation}-{date_str}-ERROR"

#         # Format: ABBR-DDMMYY-XXXX
#         lot_name = f"{abbreviation}{date_str}-{seq_number}"
#         return lot_name


#     @api.onchange('product_id')
#     def _onchange_product_id_generate_lot(self):
#         """Generate lot name when product is selected"""
#         if self.product_id and (not self.name or self.name == ''):
#             self.name = self._get_default_lot_name()









# from odoo import fields, models, api # type: ignore
# from odoo.exceptions import UserError # type: ignore
# import datetime
# from odoo.tools.translate import _ # type: ignore # Ensure this import is present for UserError messages

# class StockLot(models.Model): # Changed class name for clarity, though not strictly required
#     _inherit = 'stock.lot' # <--- CRITICAL CHANGE: Inheriting stock.lot

#     @api.model
#     def _get_parent_lot_name(self, product_id):
#         """
#         Generates the default new Parent Lot Name.
#         """
#         # ... (Your sequence generation logic is fine, but we'll clean up the call) ...
#         product = self.env['product.product'].browse(product_id)
#         abbreviation = product.product_tmpl_id.lot_abbreviation if product and product.exists() else 'XX'
        
#         if not abbreviation:
#              abbreviation = 'XX'

#         today = fields.Date.today()
#         date_str = today.strftime('%d%m%y')
#         dynamic_prefix = f"{abbreviation}{date_str}-"
        
#         sequence = self.env['ir.sequence'].next_by_code(
#             'parent.lot.daily.sequence',
#             sequence_date=today
#         )

#         if not sequence or sequence == '%s':
#              raise UserError(_("Lot Sequence Error: Could not retrieve sequence. Please check 'parent.lot.daily.sequence' configuration."))
        
#         final_lot_name = sequence % dynamic_prefix
#         return final_lot_name

#     # The create override for applying the default name (as discussed for stability)
#     @api.model
#     def create(self, vals):
#         # We need to ensure the standard Odoo lot sequencing for other products is not broken.
#         # This check is complex in older versions, so we prioritize the custom sequence if
#         # the name is missing and we have the context needed to generate it.

#         # Check if a name is missing AND we have the product context to generate one
#         product_id = vals.get('product_id') or self._context.get('default_product_id')
        
#         if not vals.get('name') and product_id:
#             vals['name'] = self._get_parent_lot_name(product_id)

#         return super(StockLot, self).create(vals)
    
    # NOT E : You do not need to redefine fields.Char(name=...) as we are using the create() override.








# from odoo import fields, models, api # type: ignore
# from odoo.exceptions import UserError # type: ignore

# class StockLot(models.Model):
#     _inherit = 'stock.lot'
#     _description = 'Stock Lot Extension'

#     # Override the name field to add our custom default
#     name = fields.Char(
#         'Lot/Serial Number',
#         default=lambda self: self._get_default_lot_name(),
#         required=True,
#         help="Unique Lot/Serial Number"
#     )

#     @api.model
#     def _get_default_lot_name(self):
#         """Generate default lot name with format: ABBR-DDMMYY-XXXX"""
#         # Try to get product_id from context
#         product_id = self._context.get('default_product_id') or self._context.get('product_id')
        
#         if not product_id:
#             # Return empty string if no product in context
#             # User will need to fill it manually or it will be set when product is selected
#             return ''
            
#         product = self.env['product.product'].browse(product_id)
#         if not product.exists():
#             return ''
            
#         abbreviation = product.product_tmpl_id.lot_abbreviation or 'XX'
        
#         today = fields.Date.today()
#         date_str = today.strftime('%d%m%y')
        
#         # Get the next sequence number for today
#         sequence_code = 'parent.lot.daily.sequence'
#         seq_number = self.env['ir.sequence'].next_by_code(sequence_code)
        
#         if not seq_number:
#             return f"{abbreviation}-{date_str}-ERROR"
        
#         # Format: ABBR-DDMMYY-XXXX
#         lot_name = f"{abbreviation}-{date_str}-{seq_number}"
#         return lot_name

#     @api.onchange('product_id')
#     def _onchange_product_id_generate_lot(self):
#         """Generate lot name when product is selected"""
#         if self.product_id and (not self.name or self.name == ''):
#             self.name = self._get_default_lot_name()








# from odoo import fields, models, api # type: ignore
# from datetime import date
# from odoo.exceptions import UserError # type: ignore


# class StockProductionLot(models.Model):
#     _inherit = 'stock.production.lot'

#     @api.model
#     def _generate_lot_name(self, product_id):
#         """Generate lot name with format: ABBR-DDMMYY-XXXX"""
#         product = self.env['product.product'].browse(product_id)
#         abbreviation = product.product_tmpl_id.lot_abbreviation or 'XX'
        
#         today = fields.Date.today()
#         date_str = today.strftime('%d%m%y')
        
#         # Get the next sequence number for today
#         sequence_code = 'parent.lot.daily.sequence'
#         seq_number = self.env['ir.sequence'].next_by_code(sequence_code)
        
#         if not seq_number:
#             raise UserError(f"Sequence '{sequence_code}' not found. Please contact administrator.")
        
#         # Format: ABBR-DDMMYY-XXXX
#         lot_name = f"{abbreviation}-{date_str}-{seq_number}"
#         return lot_name

#     @api.model_create_multi
#     def create(self, vals_list):
#         """Override create to auto-generate lot names"""
#         for vals in vals_list:
#             # Only generate if name is not provided or is empty
#             if not vals.get('name') or vals.get('name', '').strip() == '':
#                 product_id = vals.get('product_id') or self._context.get('default_product_id')
                
#                 if product_id:
#                     vals['name'] = self._generate_lot_name(product_id)
#                 else:
#                     raise UserError("Product must be specified to generate lot number.")
        
#         return super(StockProductionLot, self).create(vals_list)








# from odoo import fields, models, api # type: ignore
# from odoo.exceptions import UserError # type: ignore
# import datetime

# class StockProductionLot(models.Model):
#     _inherit = 'stock.production.lot'

#     @api.model
#     def _get_parent_lot_name(self):
#         """
#         Generates the default new Parent Lot Name.
#         This method will be called when 'name' is empty upon lot creation.
#         """
#         # 1. Get Product Abbreviation (We need a way to get the product, often via context)
#         # For a truly generic default, we can't reliably get the product here without context.
#         # We'll use a placeholder and rely on the user to select the product first, 
#         # but for now, we'll get the abbreviation from the product if context is available.
#         product_id = self._context.get('default_product_id')
#         abbreviation = self.env['product.product'].browse(product_id).product_tmpl_id.lot_abbreviation if product_id else 'XX'
        
#         # Fallback if product context is missing or abbreviation is not set
#         if not abbreviation:
#              abbreviation = 'XX'

#         # 2. Get Date String (DDMMYY format)
#         today = fields.Date.today()
#         date_str = today.strftime('%d%m%y')

#         # 3. Create Dynamic Prefix
#         dynamic_prefix = f"{abbreviation}{date_str}-"
        
#         # 4. Fetch Next Sequence using dynamic prefix and date
#         sequence = self.env['ir.sequence'].next_by_code(
#             'parent.lot.daily.sequence',
#             sequence_date=today
#         )

#         if not sequence or sequence == '%s':
#             # Fallback if sequence is misconfigured
#             return f"{dynamic_prefix}ERROR" 
        
#         # 5. Format the final name: The sequence returns %s0001, so we substitute %s
#         final_lot_name = sequence % dynamic_prefix
        
#         return final_lot_name
    
#     # We don't need to explicitly override the name field if Odoo calls the default= function
#     # during creation when the field is empty, which it does.

#     # Apply the method as the default value for the name field
#     name = fields.Char(
#         'Lot/Serial Number', 
#         required=True, 
#         default=_get_parent_lot_name, 
#         help="Unique Lot/Serial Number for this product."
#     )






# from odoo import fields, models, api
# from odoo.exceptions import UserError
# import datetime

# class StockProductionLot(models.Model):
#     _inherit = 'stock.production.lot'

#     @api.model
#     def _get_parent_lot_name(self):
#         # ... (Your sequence generation logic remains here) ...
#         product_id = self._context.get('default_product_id')
        
#         # Check if product_id is in context and get abbreviation
#         product = self.env['product.product'].browse(product_id) if product_id else self.env['product.product']
#         abbreviation = product.product_tmpl_id.lot_abbreviation if product and product.exists() else 'XX'
        
#         if not abbreviation:
#              abbreviation = 'XX'

#         today = fields.Date.today()
#         date_str = today.strftime('%d%m%y')
#         dynamic_prefix = f"{abbreviation}{date_str}-"
        
#         sequence = self.env['ir.sequence'].next_by_code(
#             'parent.lot.daily.sequence',
#             sequence_date=today
#         )

#         if not sequence or sequence == '%s':
#             return f"{dynamic_prefix}ERROR" 
        
#         final_lot_name = sequence % dynamic_prefix
#         return final_lot_name
    
#     # Apply the method as the default value for the name field
#     name = fields.Char(
#         'Lot/Serial Number', 
#         required=True, 
#         default=_get_parent_lot_name, 
#         help="Unique Lot/Serial Number for this product."
#     )






# from odoo import fields, models, api
# from odoo.exceptions import UserError
# import datetime

# class StockProductionLot(models.Model):
#     _inherit = 'stock.production.lot'

#     # The sequence generation logic remains the same
#     @api.model
#     def _get_parent_lot_name(self, product_id):
#         # We pass product_id directly instead of relying on self._context
#         product = self.env['product.product'].browse(product_id)
#         abbreviation = product.product_tmpl_id.lot_abbreviation if product and product.exists() else 'XX'
        
#         if not abbreviation:
#              abbreviation = 'XX'

#         today = fields.Date.today()
#         date_str = today.strftime('%d%m%y')
#         dynamic_prefix = f"{abbreviation}{date_str}-"
        
#         sequence = self.env['ir.sequence'].next_by_code(
#             'parent.lot.daily.sequence',
#             sequence_date=today
#         )

#         if not sequence or sequence == '%s':
#             return f"{dynamic_prefix}ERROR" 
        
#         final_lot_name = sequence % dynamic_prefix
#         return final_lot_name

#     # CRITICAL CHANGE: Overrides create() to apply default name AFTER model loading
#     @api.model
#     def create(self, vals):
#         if not vals.get('name', '').startswith(self.env['ir.sequence'].get('stock.lot.serial')):
#             # The standard Odoo sequence check. If it's not the standard sequence,
#             # it means the user is trying to create a new one, OR the field is empty.
            
#             # 1. Check if name is missing or if it's currently a placeholder
#             if not vals.get('name') or vals['name'] == self.env['stock.production.lot']._fields['name'].default:
#                 # 2. Get the product ID, either from vals (if in context) or fallback
#                 product_id = vals.get('product_id') or self._context.get('default_product_id')
                
#                 if product_id:
#                     vals['name'] = self._get_parent_lot_name(product_id)

#         return super(StockProductionLot, self).create(vals)

    # REMOVED: The name = fields.Char(default=_get_parent_lot_name) definition
    # We now rely on the inherited name field and apply the logic in create()








# from odoo import fields, models, api
# from datetime import date

# class StockProductionLot(models.Model):
#     _inherit = 'stock.production.lot'

#     @api.model
#     def _generate_lot_name(self, product_id):
#         """Generate lot name with format: ABBR-DDMMYY-XXXX"""
#         product = self.env['product.product'].browse(product_id)
#         abbreviation = product.product_tmpl_id.lot_abbreviation or 'XX'
        
#         today = fields.Date.today()
#         date_str = today.strftime('%d%m%y')
        
#         # Get the next sequence number for today
#         sequence_code = 'parent.lot.daily.sequence'
#         seq_number = self.env['ir.sequence'].next_by_code(sequence_code)
        
#         if not seq_number:
#             raise UserError(f"Sequence '{sequence_code}' not found. Please contact administrator.")
        
#         # Format: ABBR-DDMMYY-XXXX
#         lot_name = f"{abbreviation}-{date_str}-{seq_number}"
#         return lot_name

#     @api.model_create_multi
#     def create(self, vals_list):
#         """Override create to auto-generate lot names"""
#         for vals in vals_list:
#             # Only generate if name is not provided or is empty
#             if not vals.get('name') or vals.get('name', '').strip() == '':
#                 product_id = vals.get('product_id') or self._context.get('default_product_id')
                
#                 if product_id:
#                     vals['name'] = self._generate_lot_name(product_id)
#                 else:
#                     raise UserError("Product must be specified to generate lot number.")
        
#         return super(StockProductionLot, self).create(vals_list)