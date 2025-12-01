from odoo import models, fields, api, _ # type: ignore
from odoo.exceptions import UserError # type: ignore

class LotLabelWizard(models.TransientModel):
    _name = 'lot.label.wizard'
    _description = 'Lot Label Print Wizard'

    lot_ids = fields.Many2many(
        'stock.lot',
        string='Lots',
        required=True
    )
    
    label_count = fields.Integer(
        string='Number of Labels',
        default=1,
        required=True,
        help="Number of identical labels to print for each lot"
    )

    @api.constrains('label_count')
    def _check_label_count(self):
        for record in self:
            if record.label_count < 1:
                raise UserError(_("Number of labels must be at least 1"))
            if record.label_count > 50:  # Reasonable limit
                raise UserError(_("Number of labels cannot exceed 50"))

    def action_print_labels(self):
        """Print labels with specified count"""
        if not self.lot_ids:
            raise UserError(_("No lots selected for printing"))
        
        # Pass the label count to the report context
        return self.env.ref('custom_rsfp_module.action_report_lot_label_custom').with_context(
            label_count=self.label_count,
            # (Optional but recommended) Explicitly expose range to QWeb context
            range=range,
        ).report_action(self.lot_ids)