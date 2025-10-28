from odoo import models, fields, api, _ # type: ignore
from odoo.exceptions import UserError, ValidationError # type: ignore
import logging

_logger = logging.getLogger(__name__)

class CustomSortingReport(models.Model):
    _name = 'custom.sorting.report'
    _description = 'Product Sorting Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # Header Details
    name = fields.Char(
        string='Sorting Report Reference', 
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
    parent_lot_id = fields.Many2one(
        'stock.lot',
        string='Parent Lot/Batch',
        required=True,
        domain="[('id', 'in', available_lot_ids)]",
        help="The main lot/batch to be sorted into grades"
    )
    
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        related='parent_lot_id.purchase_order_id',
        store=True,
        readonly=True
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        related='parent_lot_id.product_id',
        store=True,
        readonly=True
    )
    
    available_lot_ids = fields.Many2many(
        'stock.lot',
        compute='_compute_available_lots',
        store=False
    )
    
    sorting_date = fields.Date(
        string='Sorting Date',
        required=True,
        default=fields.Date.today
    )
    
    sorter_id = fields.Many2one(
        'res.users',
        string='Sorted By',
        default=lambda self: self.env.user,
        required=True
    )
    
    sorting_location_id = fields.Many2one(
        'stock.location',
        string='Sorting Location',
        required=True
    )

    # Parent Lot Quantity Information
    parent_qty_total = fields.Float(
        string='Parent Lot Total Quantity',
        related='parent_lot_id.product_qty',
        readonly=True
    )

    # Sorting Quantities
    qty_grade_a = fields.Float(
        string='Grade A Qty',
        digits='Product Unit of Measure',
        default=0.0
    )
    qty_grade_b = fields.Float(
        string='Grade B Qty',
        digits='Product Unit of Measure',
        default=0.0
    )
    qty_grade_c = fields.Float(
        string='Grade C Qty',
        digits='Product Unit of Measure',
        default=0.0
    )

    # Computed Fields
    qty_total_sorted = fields.Float(
        string='Total Sorted Qty',
        compute='_compute_total_sorted',
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

    notes = fields.Text(string='Sorting Notes')

    @api.depends('qty_grade_a', 'qty_grade_b', 'qty_grade_c')
    def _compute_total_sorted(self):
        for record in self:
            record.qty_total_sorted = record.qty_grade_a + record.qty_grade_b + record.qty_grade_c

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
            
            # Get lots for this product that have available quantity
            lots = self.env['stock.lot'].search([
                ('product_id', '=', record.product_id.id),
                ('product_qty', '>', 0)
            ])
            
            record.available_lot_ids = [(6, 0, lots.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.sorting.report') or _('New')
        return super().create(vals_list)

    @api.constrains('qty_grade_a', 'qty_grade_b', 'qty_grade_c', 'parent_qty_total')
    def _check_sorting_quantities(self):
        for record in self:
            if record.qty_total_sorted > record.parent_qty_total:
                raise ValidationError(_(
                    "Total sorted quantity (%.2f) cannot exceed parent lot quantity (%.2f)"
                ) % (record.qty_total_sorted, record.parent_qty_total))

    def action_confirm(self):
        """Confirm the sorting report and create child lots"""
        for record in self:
            record._validate_sorting_data()
            record._create_child_lots()
            record.write({'state': 'confirmed'})
            record.message_post(
                body=_("Sorting Report confirmed by %s") % self.env.user.name
            )
        
        return self._print_sorting_report()

    def _validate_sorting_data(self):
        """Validate sorting data before confirmation"""
        self.ensure_one()
        
        if not self.parent_lot_id:
            raise UserError(_("Parent Lot is required."))
        
        if abs(self.qty_total_sorted - self.parent_qty_total) > 0.01:
            raise UserError(_(
                "Total sorted quantity (%.2f) must equal parent lot quantity (%.2f)"
            ) % (self.qty_total_sorted, self.parent_qty_total))
        
        if self.qty_total_sorted <= 0:
            raise UserError(_("At least one grade must have quantity > 0."))

    def _create_child_lots(self):
        """Create child lots based on sorting quantities"""
        self.ensure_one()
        
        if self.inventory_processed:
            return True

        stock_location = self.env.ref('stock.stock_location_stock')
        parent_lot_name = self.parent_lot_id.name
        created_lots = []

        # Define grades and their quantities
        grades = [
            ('A', self.qty_grade_a),
            ('B', self.qty_grade_b),
            ('C', self.qty_grade_c)
        ]

        for grade_letter, qty in grades:
            if qty > 0:
                child_lot_name = f"{parent_lot_name}-{grade_letter}"
                
                # Get graded product
                graded_product = self._get_graded_product(grade_letter)
                if not graded_product:
                    continue

                # Create child lot
                child_lot = self.env['stock.lot'].create({
                    'name': child_lot_name,
                    'product_id': graded_product.id,
                    'ref': parent_lot_name,
                    'parent_lot_id': self.parent_lot_id.id
                })

                # Update inventory
                self.env['stock.quant']._update_available_quantity(
                    graded_product,
                    stock_location,
                    qty,
                    lot_id=child_lot
                )

                # Reduce parent lot quantity
                self.env['stock.quant']._update_available_quantity(
                    self.product_id,
                    stock_location,
                    -qty,
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

    def _print_sorting_report(self):
        """Print sorting report with child lot labels"""
        self.ensure_one()
        report = self.env.ref('custom_rsfp_module.action_report_sorting_detail')
        return report.report_action(self)

    def action_reset_to_draft(self):
        """Reset to draft state"""
        for record in self:
            record.write({'state': 'draft'})
        return True