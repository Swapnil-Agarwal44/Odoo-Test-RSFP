from odoo import models, fields, api, _ # type: ignore
from odoo.exceptions import UserError, ValidationError # type: ignore
import logging

_logger = logging.getLogger(__name__)

class CustomQualityImage(models.Model):
    _name = 'custom.quality.image'
    _description = 'Quality Report Image Attachments'

    quality_report_id = fields.Many2one(
        'custom.quality.report',
        string='Quality Report',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(string='Description', required=True)
    image = fields.Binary(string='Image', required=True)
    location = fields.Char(string='Capture Location/Context')

class CustomQualityReport(models.Model):
    _name = 'custom.quality.report'
    _description = 'Quality Testing Report'
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

    # Reference Information
    child_lot_id = fields.Many2one(
        'stock.lot',
        string='Child Lot Reference',
        required=True,
        domain="[('parent_lot_id', '!=', False)]",
        help="The child lot being tested"
    )

    parent_lot_id = fields.Many2one(
        'stock.lot',
        string='Parent Lot',
        related='child_lot_id.parent_lot_id',
        store=True,
        readonly=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        related='child_lot_id.product_id',
        store=True,
        readonly=True
    )

    sorting_report_id = fields.Many2one(
        'custom.sorting.report',
        string='Related Sorting Report',
        compute='_compute_sorting_report',
        store=True
    )

    # Testing Information
    testing_date = fields.Date(
        string='Testing Date',
        required=True,
        default=fields.Date.today
    )

    tester_id = fields.Many2one(
        'res.users',
        string='Tested By',
        default=lambda self: self.env.user,
        required=True
    )

    test_location_id = fields.Many2one(
        'stock.location',
        string='Testing Location',
        required=True
    )

    # Lot Quantity Information
    lot_qty_total = fields.Float(
        string='Lot Total Quantity',
        related='child_lot_id.product_qty',
        readonly=True
    )

    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id'
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

    # Images
    image_ids = fields.One2many(
        'custom.quality.image',
        'quality_report_id',
        string='Test Images'
    )

    # Notes
    notes = fields.Text(string='Quality Testing Notes')

    @api.depends('child_lot_id', 'child_lot_id.parent_lot_id')
    def _compute_sorting_report(self):
        for record in self:
            if record.child_lot_id and record.child_lot_id.parent_lot_id:
                sorting_report = self.env['custom.sorting.report'].search([
                    ('parent_lot_id', '=', record.child_lot_id.parent_lot_id.id),
                    ('state', '=', 'confirmed')
                ], limit=1)
                record.sorting_report_id = sorting_report
            else:
                record.sorting_report_id = False

    @api.depends('lot_qty_total', 'rate_per_kg')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = record.lot_qty_total * record.rate_per_kg

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.quality.report') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        """Confirm the quality report"""
        for record in self:
            record._validate_quality_data()
            record.write({'state': 'confirmed'})
            record.message_post(
                body=_("Quality Report confirmed by %s") % self.env.user.name
            )
        
        return self._print_quality_report()

    def _validate_quality_data(self):
        """Validate quality data before confirmation"""
        self.ensure_one()
        
        if not self.child_lot_id:
            raise UserError(_("Child Lot reference is required."))
        
        if not self.tester_id:
            raise UserError(_("Tester is required."))
        
        if not self.test_location_id:
            raise UserError(_("Test Location is required."))

    def _print_quality_report(self):
        """Print quality report"""
        self.ensure_one()
        report = self.env.ref('custom_rsfp_module.action_report_quality_detail')
        return report.report_action(self)

    def action_reset_to_draft(self):
        """Reset to draft state"""
        for record in self:
            record.write({'state': 'draft'})
        return True