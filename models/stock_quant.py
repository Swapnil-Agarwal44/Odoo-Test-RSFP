from odoo import models, api # type: ignore
import logging

_logger = logging.getLogger(__name__)

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    @api.model
    def _update_available_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, in_date=None):
        """Override to set arrived_quantity when first adding stock to a lot"""
        
        # Call the original method first
        result = super(StockQuant, self)._update_available_quantity(
            product_id, location_id, quantity, lot_id=lot_id, 
            package_id=package_id, owner_id=owner_id, in_date=in_date
        )
        
        # If we have a lot_id and this is a positive quantity addition
        if lot_id and quantity > 0 and location_id.usage == 'internal':
            try:
                # Check if this is the first quantity assignment to the lot
                if hasattr(lot_id, '_set_arrived_quantity_if_needed'):
                    lot_id._set_arrived_quantity_if_needed(quantity)
                    _logger.info(f"Attempted to set arrived_quantity for lot {lot_id.name} with qty {quantity}")
            except Exception as e:
                _logger.warning(f"Failed to set arrived_quantity for lot {lot_id.name if lot_id else 'unknown'}: {e}")
        
        return result