from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # NEW FIELD: Abbreviation used for dynamic Lot numbering
    lot_abbreviation = fields.Char(
        string='Lot Abbreviation', 
        size=5, 
        # required=True, 
        help="2-5 letter code used for automatic Parent Lot numbering (e.g., DM for Dried Mango)."
    )

    _sql_constraints = [
        ('lot_abbreviation_unique', 
         'UNIQUE (lot_abbreviation)',
         'The Product Abbreviation must be unique across all products!')
    ]