from odoo import fields, models, api # type: ignore
import logging

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    enquiry_ids = fields.Many2many(
        'rsfp.enquiry.id',
        string='Enquiry IDs',
        help="External Enquiry IDs related to this Purchase Order/RFQ."
    )

# NEW: Extend Purchase Order Line to include assigned lot information
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    assigned_lot_id = fields.Many2one(
        'stock.lot',
        string='Assigned Parent Lot',
        compute='_compute_assigned_lot',
        store=False,  # Changed to False to avoid storage issues
        help="The parent lot assigned to this purchase order line during receipt"
    )

    lot_assigned = fields.Char(
        string='Lot Assigned',
        compute='_compute_lot_assigned',
        help="Display name of the assigned parent lot"
    )

    def _compute_assigned_lot(self):
        """Compute the assigned lot from completed stock moves"""
        for line in self:
            try:
                # Search for stock move lines related to this purchase line
                move_lines = self.env['stock.move.line'].search([
                    ('picking_id.origin', '=', line.order_id.name),
                    ('product_id', '=', line.product_id.id),
                    ('state', '=', 'done'),
                    ('lot_id', '!=', False)
                ], limit=1)
                
                if move_lines:
                    line.assigned_lot_id = move_lines.lot_id
                else:
                    line.assigned_lot_id = False
                    
            except Exception as e:
                _logger.error(f"Error computing assigned lot for line {line.id}: {str(e)}")
                line.assigned_lot_id = False

    def _compute_lot_assigned(self):
        """Compute the lot assigned field"""
        for line in self:
            line.lot_assigned = line.assigned_lot_id.name if line.assigned_lot_id else ''