from . import models
# If we had controllers, we'd add: from . import controllers
# If we had wizards/reports in their own directory, we'd import them here too.

def post_init_hook(cr, registry):
    """Post-installation hook to migrate existing lots"""
    from odoo.api import Environment
    import logging
    
    _logger = logging.getLogger(__name__)
    
    try:
        _logger.info("Starting post-install migration for arrived_quantity")
        
        env = Environment(cr, 1, {})
        stock_lot_model = env['stock.lot']
        
        # Run the migration method
        stock_lot_model._migrate_existing_lots_arrived_quantity()
        
        _logger.info("Post-install migration completed successfully")
    except Exception as e:
        _logger.error(f"Post-install migration failed: {e}")
        # Don't raise the exception to prevent installation failure
        # but log it for troubleshooting