from odoo import fields, models # type: ignore

# This file includes a new field called lot_abbreviation in the products.template field, to allow for a admin to assign a unique abreviation to the products in the inventory. 
# This is being used for the custom lot sequence creation of the lot of the purchase order.  
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