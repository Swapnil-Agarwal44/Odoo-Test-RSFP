from odoo import models # type: ignore

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    def _get_default_location_names(self):
        """
        Override this method to return an empty list for specific custom warehouses,
        thereby preventing the creation of default locations (Stock, Input, Output, etc.).
        """
        # If the warehouse code matches one of your custom warehouses (DS or PA),
        # return an empty dictionary.
        if self.code in ('DS', 'PA'):
            return {}
        
        # For all other warehouses (standard Odoo flow), call the original method.
        return super(StockWarehouse, self)._get_default_location_names()