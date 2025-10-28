from odoo import models, fields, api, _ # type: ignore
from odoo.exceptions import UserError, ValidationError # type: ignore
import logging

_logger = logging.getLogger(__name__)

class CustomQualityImage(models.Model):
    _name = 'custom.quality.image'
    _description = 'Quality Grading Report Image Attachments'

    quality_grading_id = fields.Many2one(
        'custom.quality.grading',
        string='Quality Grading Report',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(string='Description', required=True)
    image = fields.Binary(string='Image', required=True)
    location = fields.Char(string='Capture Location/Context')

class CustomQualityTestLine(models.Model):
    _name = 'custom.quality.test.line'
    _description = 'Quality Test Line'

    quality_grading_id = fields.Many2one(
        'custom.quality.grading',
        string='Quality Grading Report',
        required=True,
        ondelete='cascade'
    )

    graded_product_id = fields.Many2one(
        'product.product',
        string='Graded Product',
        required=True,
        domain="[('id', 'in', available_graded_products)]"
    )

    available_graded_products = fields.Many2many(
        'product.product',
        compute='_compute_available_graded_products',
        store=False
    )

    grade_letter = fields.Char(
        string='Grade',
        compute='_compute_grade_letter',
        store=True
    )

    # Quality Characteristics (Boolean)
    uniform_color = fields.Boolean(string='Uniform Color', default=True)
    visible_mold = fields.Boolean(string='Visible Mold', default=False)
    physical_damage = fields.Boolean(string='Physical Damage', default=False)
    pest_free = fields.Boolean(string='Pest Free', default=True)

    # Quality Characteristics (Selections)
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

    # Numeric Measurements
    moisture = fields.Float(
        string='Moisture (%)',
        digits=(6, 2),
        help="Percentage of moisture in the product"
    )

    qty_of_grade = fields.Float(
        string='Quantity of Grade',
        digits='Product Unit of Measure',
        readonly=True
    )

    # Valuation
    rate_per_kg = fields.Float(
        string='Rate/Kg',
        digits='Product Price',
        required=True,
        default=0.0
    )

    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
        readonly=True
    )

    @api.depends('graded_product_id')
    def _compute_grade_letter(self):
        for line in self:
            if line.graded_product_id:
                name = line.graded_product_id.name.upper()
                if 'GRADE A' in name:
                    line.grade_letter = 'A'
                elif 'GRADE B' in name:
                    line.grade_letter = 'B'
                elif 'GRADE C' in name:
                    line.grade_letter = 'C'
                else:
                    line.grade_letter = ''
            else:
                line.grade_letter = ''

    @api.depends('qty_of_grade', 'rate_per_kg')
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = line.qty_of_grade * line.rate_per_kg

    @api.depends('quality_grading_id.product_id')
    def _compute_available_graded_products(self):
        for line in self:
            if not line.quality_grading_id.product_id:
                line.available_graded_products = [(6, 0, [])]
                continue
            
            base_name = line.quality_grading_id.product_id.name.replace(' - Bulk', '').replace('Bulk', '')
            
            graded_products = self.env['product.product'].search([
                ('name', 'ilike', base_name),
                ('name', 'ilike', 'grade'),
                ('tracking', '=', 'lot')
            ])
            
            line.available_graded_products = [(6, 0, graded_products.ids)]

class CustomQualityGrading(models.Model):
    _name = 'custom.quality.grading'
    _description = 'Quality Grading Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # Header Details
    name = fields.Char(
        string='Quality Report Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )

    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', readonly=True, tracking=True)

    # Basic Information
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    parent_lot_id = fields.Many2one(
        'stock.lot',
        string='Parent Lot/Batch',
        required=True,
        domain="[('id', 'in', available_lot_ids)]",
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="The main lot/batch being tested and graded"
    )

    available_lot_ids = fields.Many2many(
        'stock.lot',
        compute='_compute_available_lots',
        store=False
    )

    receipt_date = fields.Date(
        string='Receipt/Testing Date',
        required=True,
        default=fields.Date.today,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    tester_id = fields.Many2one(
        'res.users',
        string='Tested By',
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    test_location_id = fields.Many2one(
        'stock.location',
        string='Test Location',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    # Quantity Information
    qty_received = fields.Float(
        string='Total Qty Received',
        digits='Product Unit of Measure',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    qty_grade_a = fields.Float(
        string='Grade A Qty',
        digits='Product Unit of Measure',
        default=0.0,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    qty_grade_b = fields.Float(
        string='Grade B Qty',
        digits='Product Unit of Measure',
        default=0.0,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    qty_grade_c = fields.Float(
        string='Grade C Qty',
        digits='Product Unit of Measure',
        default=0.0,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    qty_total_graded = fields.Float(
        string='Total Graded Qty',
        compute='_compute_total_graded',
        store=True
    )

    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id'
    )

    # Processing Status
    inventory_processed = fields.Boolean(
        string="Child Lots Created",
        default=False,
        copy=False
    )

    # Created Child Lots
    child_lot_ids = fields.Many2many(
        'stock.lot',
        compute='_compute_child_lot_ids',
        string='Created Child Lots'
    )

    # Test Lines
    test_line_ids = fields.One2many(
        'custom.quality.test.line',
        'quality_grading_id',
        string='Quality Test Lines'
    )

    # Images
    image_ids = fields.One2many(
        'custom.quality.image',
        'quality_grading_id',
        string='Test Images'
    )

    notes = fields.Text(string='General Remarks and Notes')

    @api.depends('qty_grade_a', 'qty_grade_b', 'qty_grade_c')
    def _compute_total_graded(self):
        for record in self:
            record.qty_total_graded = record.qty_grade_a + record.qty_grade_b + record.qty_grade_c

    @api.depends('parent_lot_id', 'inventory_processed')
    def _compute_child_lot_ids(self):
        for record in self:
            if not record.parent_lot_id or not record.inventory_processed:
                record.child_lot_ids = [(6, 0, [])]
                continue
            
            parent_lot_name = record.parent_lot_id.name
            child_lots = self.env['stock.lot'].search([
                ('ref', '=', parent_lot_name),
                ('parent_lot_id', '=', record.parent_lot_id.id)
            ])
            
            record.child_lot_ids = [(6, 0, child_lots.ids)]

    @api.depends('product_id')
    def _compute_available_lots(self):
        for record in self:
            if not record.product_id:
                record.available_lot_ids = [(6, 0, [])]
                continue
            
            lots = self.env['stock.lot'].search([
                ('product_id', '=', record.product_id.id),
                ('product_qty', '>', 0)
            ])
            
            record.available_lot_ids = [(6, 0, lots.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.quality.grading') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        """Confirm the quality grading report and create child lots"""
        for record in self:
            record._validate_grading_data()
            record._create_test_lines()
            record._create_child_lots()
            record.write({'state': 'confirmed'})
            record.message_post(
                body=_("Quality Grading Report confirmed by %s") % self.env.user.name
            )
        
        return self._print_quality_report()

    def _validate_grading_data(self):
        """Validate grading data before confirmation"""
        self.ensure_one()
        
        if not self.parent_lot_id:
            raise UserError(_("Parent Lot is required."))
        
        if abs(self.qty_total_graded - self.qty_received) > 0.01:
            raise UserError(_(
                "Total graded quantity (%.2f) must equal received quantity (%.2f)"
            ) % (self.qty_total_graded, self.qty_received))
        
        if self.qty_total_graded <= 0:
            raise UserError(_("At least one grade must have quantity > 0."))

    def _create_test_lines(self):
        """Create test lines for each grade with quantity > 0"""
        self.ensure_one()
        
        # Clear existing test lines
        self.test_line_ids.unlink()
        
        grades = [
            ('A', self.qty_grade_a),
            ('B', self.qty_grade_b),
            ('C', self.qty_grade_c)
        ]
        
        for grade_letter, qty in grades:
            if qty > 0:
                graded_product = self._get_graded_product(grade_letter)
                if graded_product:
                    self.env['custom.quality.test.line'].create({
                        'quality_grading_id': self.id,
                        'graded_product_id': graded_product.id,
                        'qty_of_grade': qty
                    })

    def _create_child_lots(self):
        """Create child lots based on grading quantities"""
        self.ensure_one()
        
        if self.inventory_processed:
            return True

        stock_location = self.env.ref('stock.stock_location_stock')
        parent_lot_name = self.parent_lot_id.name
        created_lots = []

        for test_line in self.test_line_ids:
            if test_line.qty_of_grade > 0:
                child_lot_name = f"{parent_lot_name}-{test_line.grade_letter}"
                
                # Create child lot
                child_lot = self.env['stock.lot'].create({
                    'name': child_lot_name,
                    'product_id': test_line.graded_product_id.id,
                    'ref': parent_lot_name,
                    'parent_lot_id': self.parent_lot_id.id
                })

                # Update inventory
                self.env['stock.quant']._update_available_quantity(
                    test_line.graded_product_id,
                    stock_location,
                    test_line.qty_of_grade,
                    lot_id=child_lot
                )

                # Reduce parent lot quantity
                self.env['stock.quant']._update_available_quantity(
                    self.product_id,
                    stock_location,
                    -test_line.qty_of_grade,
                    lot_id=self.parent_lot_id
                )

                created_lots.append(child_lot_name)

        self.write({'inventory_processed': True})
        
        if created_lots:
            self.message_post(
                body=_("Child lots created: %s") % ', '.join(created_lots)
            )

        return True

    def _get_graded_product(self, grade_letter):
        """Get the graded product for a specific grade"""
        base_name = self.product_id.name.replace(' - Bulk', '').replace('Bulk', '')
        
        graded_product = self.env['product.product'].search([
            ('name', 'ilike', base_name),
            ('name', 'ilike', f'grade {grade_letter}'),
            ('tracking', '=', 'lot')
        ], limit=1)
        
        return graded_product

    def _print_quality_report(self):
        """Print quality grading report"""
        self.ensure_one()
        report = self.env.ref('custom_rsfp_module.action_report_quality_grading_detail')
        return report.report_action(self)