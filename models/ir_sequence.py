from odoo import models, api, fields

class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.model
    def next_by_code(self, sequence_code, sequence_date=None):
        """Override to handle daily reset for parent lot sequence"""
        if sequence_code == 'parent.lot.daily.sequence':
            return self._get_daily_lot_sequence()
        return super(IrSequence, self).next_by_code(sequence_code, sequence_date)

    @api.model
    def _get_daily_lot_sequence(self):
        """Get next sequence number, resetting daily"""
        sequence = self.search([('code', '=', 'parent.lot.daily.sequence')], limit=1)
        if not sequence:
            return False
        
        today = fields.Date.today()
        
        # Check if we have a date range for today
        date_range = self.env['ir.sequence.date_range'].search([
            ('sequence_id', '=', sequence.id),
            ('date_from', '<=', today),
            ('date_to', '>=', today)
        ], limit=1)
        
        if not date_range:
            # Create new date range for today
            date_range = self.env['ir.sequence.date_range'].create({
                'sequence_id': sequence.id,
                'date_from': today,
                'date_to': today,
                'number_next': 1,
            })
        
        # Get next number and format it
        number = date_range.number_next
        date_range.number_next += 1
        
        # Format with padding
        formatted_number = str(number).zfill(sequence.padding)
        return formatted_number