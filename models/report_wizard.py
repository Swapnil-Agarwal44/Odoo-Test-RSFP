from odoo import models, fields, api # type: ignore

# TransientModel is for creating temporary records used for forms/wizards
class CustomQualityReportWizard(models.TransientModel):
    _name = 'custom.quality.report.wizard'
    _description = 'Quality Grading Report Generation Wizard'

    # Filter Fields
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    
    # We allow filtering by product, or running the report for all products
    product_id = fields.Many2one('product.product', string='Product Filter')
    
    # Action method to be called by the "Print" button on the wizard form
    def action_print_report(self):
        """
        This method is called when the user clicks 'Print Report'.
        It will pass the wizard's filter data to the report engine.
        
        Note: The actual report definition (ir.actions.report) 
        and the QWeb template are defined in Phase 3. 
        We are preparing the structure here.
        """
        # Dictionary containing the filter values to pass to the report
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'product_id': self.product_id.id,
            'product_name': self.product_id.name or 'All Products',
            'model': 'custom.quality.grading', # The model we are querying
        }
        
        # We call the report action defined in Phase 3. 
        # The report name format is 'module_name.report_template_id'
        return self.env.ref('custom_quality_report.action_report_quality_grading').report_action(
            self, data=data
        )