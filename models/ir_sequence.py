from odoo import models, api, fields # type: ignore
import logging

_logger = logging.getLogger(__name__)

#this sequence is used to generate the proper data sequence for the customized lot sequence generation
class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.model
    def next_by_code(self, sequence_code, sequence_date=None):
        """Override to handle daily reset for custom sequences"""
        _logger.info(f"=== SEQUENCE REQUESTED: {sequence_code} ===")

        # Handle parent lot sequence
        if sequence_code == 'parent.lot.daily.sequence':
            result = self._get_daily_sequence(sequence_code, 'LOT')
            _logger.info(f"LOT sequence result: {result}")
            return result
        
        # Handle quality grading report sequence
        elif sequence_code == 'custom.quality.grading.daily':
            result = self._get_daily_sequence(sequence_code, 'QR')
            _logger.info(f"QR grading sequence result: {result}")
            return result
        
        # Handle sorting report sequence
        elif sequence_code == 'custom.sorting.report.daily':
            result = self._get_daily_sequence(sequence_code, 'SR')
            _logger.info(f"SR sorting sequence result: {result}")
            return result
        
        # Handle quality report sequence
        elif sequence_code == 'custom.quality.report.daily':
            result = self._get_daily_sequence(sequence_code, 'QR')
            _logger.info(f"QR report sequence result: {result}")
            return result
        
        _logger.info(f"Using default sequence handling for: {sequence_code}")
        return super(IrSequence, self).next_by_code(sequence_code, sequence_date)

    @api.model
    def _get_daily_sequence(self, sequence_code, prefix_code):
        """Get next sequence number with daily reset and custom formatting"""
        _logger.info(f"=== Getting daily sequence for {sequence_code} with prefix {prefix_code} ===")
        
        sequence = self.search([('code', '=', sequence_code)], limit=1)
        if not sequence:
            _logger.error(f"Sequence {sequence_code} not found!")
            return False
        
        today = fields.Date.today()
        date_str = today.strftime('%d%m%y')  # Format: DDMMYY
        
        # Check if we have a date range for today
        date_range = self.env['ir.sequence.date_range'].search([
            ('sequence_id', '=', sequence.id),
            ('date_from', '<=', today),
            ('date_to', '>=', today)
        ], limit=1)
        
        if not date_range:
            # Create new date range for today
            _logger.info(f"Creating new date range for {sequence_code} on {today}")
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
        
        # For lot sequences, return just the number (formatting done in lot model)
        if prefix_code == 'LOT':
            _logger.info(f"Returning lot sequence number: {formatted_number}")
            return formatted_number
        
        # For report sequences, return full formatted name
        full_name = f"{prefix_code}-{date_str}-{formatted_number}"
        _logger.info(f"Generated sequence: {full_name}")
        return full_name