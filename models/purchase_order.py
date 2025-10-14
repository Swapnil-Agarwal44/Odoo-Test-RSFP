from odoo import fields, models # type: ignore

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    enquiry_ids = fields.Many2many(
        'rsfp.enquiry.id',
        string='Enquiry IDs',
        help="External Enquiry IDs related to this Purchase Order/RFQ."
    )