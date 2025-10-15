from odoo import models, fields, api, _ # type: ignore
from odoo.exceptions import UserError, ValidationError # type: ignore

#This model file defines that models that are required to create and store the custom quality and grading reports. 

# --- 1. Quality Image Record Model (Child) ---
class CustomQualityImage(models.Model):
    _name = 'custom.quality.image'
    _description = 'Custom Quality Image Attachments'

    # Relation to the parent report
    grading_id = fields.Many2one('custom.quality.grading', string='Quality Report', required=True, ondelete='cascade')
    
    # Image details
    name = fields.Char(string='Description', required=True)
    image = fields.Binary(string='Image', required=True)
    location = fields.Char(string='Capture Location/Context')


    #computed fields and 
    # @api.depends('image_ids')
    # def _compute_image_rows(self):
    #     for record in self:
    #         # Group images into lists of 3
    #         record.image_rows = [
    #             record.image_ids[i:i + 3] 
    #             for i in range(0, len(record.image_ids), 3)
    #         ]

    # image_rows = fields.Many2many(
    #     'ir.attachment', string="Image Rows", compute='_compute_image_rows', store=False
    # )

# --- 2. Quality Test Line Model (Child) ---
class CustomQualityTestLine(models.Model):
    _name = 'custom.quality.test.line'
    _description = 'Grade-Specific Quality Characteristics'

    # --- Relations ---
    grading_id = fields.Many2one(
        'custom.quality.grading', 
        string='Quality Report', 
        required=True, 
        ondelete='cascade'
    )
    
    # Field to specify which Grade this test line record belongs to (A, B, or C)
    grade_type = fields.Selection([
        ('grade_a', 'Grade A'),
        ('grade_b', 'Grade B'),
        ('grade_c', 'Grade C'),
    ], string='Product Grade', required=True)

    # **START OF NEW/MODIFIED CODE**
    # NEW FIELD: The specific destination product for this grade
    graded_product_id = fields.Many2one(
        'product.product',
        string='Destination Graded Product',
        domain=[('tracking', '=', 'lot')], # Only show lot-tracked products
        required=True,
        help="The specific product record (A Grade, B Grade, etc.) this quantity will be transformed into."
    )
    # **END OF NEW/MODIFIED CODE**

    # --- Quality Characteristics (Checkboxes) ---
    uniform_color = fields.Boolean(string='Uniform Color', default=True)
    visible_mold = fields.Boolean(string='Visible Mold', default=False)
    physical_damage = fields.Boolean(string='Physical Damage', default=False)
    pest_free = fields.Boolean(string='Pest Free', default=True)

    # --- Quality Characteristics (Selections) ---
    freshness = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('acceptable', 'Acceptable'),
        ('poor', 'Poor'),
    ], string='Freshness', default='acceptable')
    
    texture = fields.Selection([
        ('tender', 'Tender'),
        ('slightly_firm', 'Slightly Firm'),
        ('tough_leathery', 'Tough/Leathery'),
    ], string='Texture', default='slightly_firm')
    
    aroma = fields.Selection([
        ('characteristic', 'Characteristic'),
        ('faint', 'Faint'),
        ('off_odor', 'Off Odor'),
    ], string='Aroma', default='characteristic')

    # --- Numeric & Valuation Fields ---
    moisture = fields.Float(
        string='Moisture (%)', 
        digits=(6, 2), 
        help="Percentage of moisture in the graded quantity."
    )
    
    rate_per_kg = fields.Float(
        string='Rate/Kg', 
        digits='Product Price', 
        required=True, 
        default=0.0
    )
    
    # Total Quantity of this specific grade (Pulled from Parent Report)
    # This field is required for the computation of total_amount
    qty_of_grade = fields.Float(
        string='Quantity (Kg)',
        compute='_compute_qty_of_grade',
        store=True,
        readonly=True
    )
    
    # Auto Computed Field: total_amount = qty_of_grade * rate_per_kg
    total_amount = fields.Float(
        string='Total Amount', 
        compute='_compute_total_amount', 
        store=True,
        readonly=True
    )

    # --- Compute Methods ---
    
    @api.depends('grade_type', 'grading_id.qty_grade_a', 'grading_id.qty_grade_b', 'grading_id.qty_grade_c')
    def _compute_qty_of_grade(self):
        for line in self:
            if line.grade_type == 'grade_a':
                line.qty_of_grade = line.grading_id.qty_grade_a
            elif line.grade_type == 'grade_b':
                line.qty_of_grade = line.grading_id.qty_grade_b
            elif line.grade_type == 'grade_c':
                line.qty_of_grade = line.grading_id.qty_grade_c
            else:
                line.qty_of_grade = 0.0

    @api.depends('qty_of_grade', 'rate_per_kg')
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = line.qty_of_grade * line.rate_per_kg

    # --- Constraint to prevent duplicate grades on one report ---
    @api.constrains('grade_type', 'grading_id')
    def _check_unique_grade_per_report(self):
        for line in self:
            domain = [
                ('grading_id', '=', line.grading_id.id),
                ('grade_type', '=', line.grade_type),
                ('id', '!=', line.id),
            ]
            if self.search(domain, limit=1):
                raise ValidationError(
                    _('A Quality Report can only have one test line entry for each grade type (%s).') % line.grade_type.capitalize()
                )

# --- 3. Quality Grading Report Model (Header/Parent) ---
class CustomQualityGrading(models.Model):
    _name = 'custom.quality.grading'
    _description = 'Custom Quality Grading Report Header'
    _inherit = ['mail.thread', 'mail.activity.mixin'] # Adds Chatter functionality (Notes, Followers)
    _rec_name = 'name'

    # Header Details
    name = fields.Char(string='Report Reference', required=True, copy=False, readonly=True, 
                       default=lambda self: _('New'))
    # Links to the built-in Purchase Order model
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order Ref', 
                                        required=True, ondelete='restrict', tracking=True)
    product_id = fields.Many2one('product.product', string='Product Tested', required=True)
    receipt_date = fields.Date(string='Testing Date', required=True, default=fields.Date.today)
    tester_id = fields.Many2one('res.users', string='Tested By', 
                                default=lambda self: self.env.user, required=True)
    
    # NEW FIELD: Test Location
    test_location_id = fields.Many2one('stock.location', string='Test Location',
                                       help="The internal location where the quality testing took place.")
    
    # NEW FIELD: Parent Lot/Batch ID (Replaces the commented-out lot_id field)
    parent_lot_id = fields.Many2one(
        'stock.production.lot', 
        string='Parent Lot/Batch', 
        required=True, # Lot is required to confirm the report and perform segregation
        help="The main Lot/Batch number assigned during the initial Purchase Receipt."
    )

    # Grading Summary Fields
    qty_received = fields.Float(string='Qty Received (Total)', required=True, digits='Product Unit of Measure')
    # Use a related field to automatically get the UoM from the product
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id')
    
    qty_grade_a = fields.Float(string='Grade A Qty', digits='Product Unit of Measure', default=0.0)
    qty_grade_b = fields.Float(string='Grade B Qty', digits='Product Unit of Measure', default=0.0)
    qty_grade_c = fields.Float(string='Grade C Qty', digits='Product Unit of Measure', default=0.0)
    
    # Computed field for validation
    qty_total_graded = fields.Float(string='Total Graded Qty', compute='_compute_total_graded', store=True)

    # One-to-Many Relationships
    test_line_ids = fields.One2many('custom.quality.test.line', 'grading_id', string='Test Lines')
    image_ids = fields.One2many('custom.quality.image', 'grading_id', string='Attached Images')

    # NEW FIELD: General Notes
    notes = fields.Text(string='General Notes/Remarks', help="Any high-level notes or remarks related to the overall quality inspection.") 

    # Computed fields and Constraints
    @api.depends('qty_grade_a', 'qty_grade_b', 'qty_grade_c')
    def _compute_total_graded(self):
        """Calculates the sum of all graded quantities."""
        for record in self:
            record.qty_total_graded = record.qty_grade_a + record.qty_grade_b + record.qty_grade_c

    @api.constrains('qty_received', 'qty_total_graded')
    def _check_quantities(self):
        """Ensures total graded quantity does not exceed quantity received."""
        for record in self:
            if record.qty_total_graded > record.qty_received:
                raise UserError(_("The total graded quantity (A+B+C) cannot exceed the quantity received."))

    @api.model_create_multi
    def create(self, vals_list):
        """Assigns the sequence number upon creation."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.quality.grading') or _('New')
        return super().create(vals_list)