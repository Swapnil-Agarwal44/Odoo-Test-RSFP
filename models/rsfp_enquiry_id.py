from odoo import fields, models, api # type: ignore

# This model represents external enquiry IDs used in RSFP system.
# It stores unique identifiers that can be linked to purchase orders for external reference and tracking purposes.

class RSFPEnquiryID(models.Model):
    _name = 'rsfp.enquiry.id'
    _description = 'RSFP External Enquiry ID'
    _rec_name = 'name'  # Make sure name field is used for display

    name = fields.Char(string='Enquiry ID', required=True, index=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)  # Add for archiving capability

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'The Enquiry ID must be unique!')
    ]

    @api.depends('name', 'description')
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.description:
                name = f"{name} - {record.description}"
            result.append((record.id, name))
        return result