from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class CustomChildLotLine(models.Model):
    _name = 'custom.child.lot.line'
    _description = 'Child Lot Creation Line'
    _order = 'sequence, id'

    creation_id = fields.Many2one(
        'custom.child.lot.creation',
        string='Creation Report',
        required=True,
        ondelete='cascade'
    )
    
    sequence = fields.Integer(string='Sequence', default=10)
    
    quantity = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
        required=True,
        default=0.0
    )
    
    notes = fields.Text(string='Notes')
    
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        required=True
    )
    
    # Created lot information (filled after confirmation)
    created_lot_id = fields.Many2one(
        'stock.lot',
        string='Created Lot',
        readonly=True,
        help="The lot created from this line"
    )
    
    created_lot_name = fields.Char(
        string='Created Lot Name',
        related='created_lot_id.name',
        readonly=True
    )
    
    # Computed fields for validation
    state = fields.Selection(
        related='creation_id.state',
        string='State',
        store=False
    )

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_("Quantity must be greater than 0"))

    @api.model
    def default_get(self, fields_list):
        """Set default location from parent lot"""
        res = super().default_get(fields_list)
        
        # Get creation_id from context
        creation_id = self.env.context.get('default_creation_id')
        if creation_id:
            creation = self.env['custom.child.lot.creation'].browse(creation_id)
            if creation.parent_lot_id:
                # Try to get parent lot's location from stock quants
                quants = self.env['stock.quant'].search([
                    ('lot_id', '=', creation.parent_lot_id.id),
                    ('quantity', '>', 0)
                ], limit=1)
                
                if quants:
                    res['location_id'] = quants.location_id.id
                else:
                    # Fallback to stock location
                    stock_location = self.env.ref('stock.stock_location_stock', raise_if_not_found=False)
                    if stock_location:
                        res['location_id'] = stock_location.id
        
        return res