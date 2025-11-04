from odoo import models, fields, api, _ # type: ignore
from odoo.exceptions import UserError, ValidationError # type: ignore
import logging

_logger = logging.getLogger(__name__)

class CustomChildLotCreation(models.Model):
    _name = 'custom.child.lot.creation'
    _description = 'Child Lot Creation Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # Header Details
    name = fields.Char(
        string='Child Lot Creation Reference', 
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

    # Parent Lot Selection (can be any lot - parent or child)
    parent_lot_id = fields.Many2one(
        'stock.lot',
        string='Source Lot',
        required=True,
        help="Select the lot to be subdivided into additional child lots"
    )
    
    # Root Parent Lot (for tracking hierarchy)
    root_parent_lot_id = fields.Many2one(
        'stock.lot',
        string='Root Parent Lot',
        compute='_compute_root_parent_lot',
        store=True,
        readonly=True,
        help="The original parent lot (root of the hierarchy)"
    )
    
    # Purchase Order Reference
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        compute='_compute_purchase_order',
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
    
    creation_date = fields.Date(
        string='Creation Date',
        required=True,
        default=fields.Date.today
    )
    
    creator_id = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        required=True
    )
    
    creation_location_id = fields.Many2one(
        'stock.location',
        string='Creation Location',
        required=True
    )

    # Source Lot Quantity
    source_qty_total = fields.Float(
        string='Source Lot Total Quantity',
        compute='_compute_source_qty_total',
        store=False,
        readonly=True,
        help="Total quantity available in the source lot"
    )

    # Store the original source quantity for reporting
    source_qty_at_creation = fields.Float(
        string='Source Quantity at Creation',
        readonly=True,
        help="Original source lot quantity when creation was performed"
    )

    # Subdivision Quantities
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
    qty_total_subdivided = fields.Float(
        string='Total Subdivided Qty',
        compute='_compute_total_subdivided',
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

    # Created Child Lots (for display as copyable text)
    child_lot_names = fields.Char(
        string='Child Lot Names',
        compute='_compute_child_lot_names',
        help="Comma-separated child lot names for easy copying"
    )

    notes = fields.Text(string='Creation Notes')

    @api.depends('parent_lot_id')
    def _compute_root_parent_lot(self):
        """Find the root parent lot by traversing up the hierarchy"""
        for record in self:
            if not record.parent_lot_id:
                record.root_parent_lot_id = False
                continue
            
            current_lot = record.parent_lot_id
            # Traverse up to find the root (lot without parent_lot_id)
            while current_lot.parent_lot_id:
                current_lot = current_lot.parent_lot_id
            
            record.root_parent_lot_id = current_lot

    @api.depends('root_parent_lot_id')
    def _compute_purchase_order(self):
        """Compute purchase order from root parent lot's stock moves"""
        for record in self:
            if not record.root_parent_lot_id:
                record.purchase_order_id = False
                continue
            
            # Find PO through stock move lines
            move_lines = self.env['stock.move.line'].search([
                ('lot_id', '=', record.root_parent_lot_id.id),
                ('state', '=', 'done'),
                ('move_id.purchase_line_id', '!=', False)
            ], limit=1)
            
            if move_lines and move_lines.move_id.purchase_line_id:
                record.purchase_order_id = move_lines.move_id.purchase_line_id.order_id
            else:
                record.purchase_order_id = False

    @api.depends('parent_lot_id', 'source_qty_at_creation', 'state')
    def _compute_source_qty_total(self):
        """Compute the total quantity of the source lot"""
        for record in self:
            if not record.parent_lot_id:
                record.source_qty_total = 0.0
                continue
            
            # If confirmed, use the stored quantity from creation time
            if record.state == 'confirmed' and record.source_qty_at_creation:
                record.source_qty_total = record.source_qty_at_creation
            else:
                # For draft records, use current lot quantity
                record.source_qty_total = record.parent_lot_id.product_qty or 0.0

    @api.depends('qty_grade_a', 'qty_grade_b', 'qty_grade_c')
    def _compute_total_subdivided(self):
        for record in self:
            record.qty_total_subdivided = record.qty_grade_a + record.qty_grade_b + record.qty_grade_c

    @api.depends('parent_lot_id', 'inventory_processed', 'name')
    def _compute_child_lot_ids(self):
        for record in self:
            if not record.parent_lot_id or not record.inventory_processed:
                record.child_lot_ids = [(6, 0, [])]
                continue
            
            # Find child lots created by this process
            # They will have names like: parent_name + grade_letter (appended, no hyphen)
            parent_lot_name = record.parent_lot_id.name
            child_lots = self.env['stock.lot'].search([
                ('name', 'in', [
                    f"{parent_lot_name}A",
                    f"{parent_lot_name}B", 
                    f"{parent_lot_name}C"
                ]),
                ('parent_lot_id', '=', record.parent_lot_id.id)
            ])
            
            record.child_lot_ids = [(6, 0, child_lots.ids)]

    @api.depends('child_lot_ids')
    def _compute_child_lot_names(self):
        """Compute comma-separated child lot names for copying"""
        for record in self:
            if record.child_lot_ids:
                record.child_lot_names = ', '.join(record.child_lot_ids.mapped('name'))
            else:
                record.child_lot_names = ''

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                # Use sequence for child lot creation
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.child.lot.creation.daily') or _('New')
        return super().create(vals_list)

    @api.constrains('qty_grade_a', 'qty_grade_b', 'qty_grade_c', 'source_qty_total')
    def _check_subdivision_quantities(self):
        # Skip validation during module installation/update
        if self.env.context.get('module_uninstall') or self.env.context.get('install_mode'):
            return
        
        for record in self:
            # Compute source quantity on the fly for validation
            source_qty = record.parent_lot_id.product_qty if record.parent_lot_id else 0.0
            total_subdivided = record.qty_grade_a + record.qty_grade_b + record.qty_grade_c
            
            if total_subdivided > source_qty:
                raise ValidationError(_(
                    "Total subdivided quantity (%.2f) cannot exceed source lot quantity (%.2f)"
                ) % (total_subdivided, source_qty))

    def action_confirm(self):
        """Confirm the child lot creation and create child lots"""
        for record in self:
            # Store the source quantity BEFORE any processing
            record.source_qty_at_creation = record.parent_lot_id.product_qty
            record._validate_subdivision_data()
            record._create_child_lots()
            record.write({'state': 'confirmed'})
            record.message_post(
                body=_("Child Lot Creation confirmed by %s") % self.env.user.name
            )
        
        return self._print_creation_report()

    def _validate_subdivision_data(self):
        """Validate subdivision data before confirmation"""
        self.ensure_one()
        
        if not self.parent_lot_id:
            raise UserError(_("Source Lot is required."))

        # Use current source quantity for validation
        source_qty = self.parent_lot_id.product_qty or 0.0
        
        if source_qty <= 0:
            raise UserError(_("Source lot has no available quantity."))
        
        if abs(self.qty_total_subdivided - self.source_qty_total) > 0.01:
            raise UserError(_(
                "Total subdivided quantity (%.2f) must equal source lot quantity (%.2f)"
            ) % (self.qty_total_subdivided, self.source_qty_total))
        
        if self.qty_total_subdivided <= 0:
            raise UserError(_("At least one grade must have quantity > 0."))

    def _create_child_lots(self):
        """Create child lots based on subdivision quantities"""
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
                # IMPORTANT: No hyphen - just append grade letter
                child_lot_name = f"{parent_lot_name}{grade_letter}"
                
                # Use same product as parent lot
                target_product = self.product_id

                # Create child lot
                child_lot = self.env['stock.lot'].create({
                    'name': child_lot_name,
                    'product_id': target_product.id,
                    'ref': self.root_parent_lot_id.name if self.root_parent_lot_id else parent_lot_name,
                    'parent_lot_id': self.parent_lot_id.id
                })

                # Add inventory for child lots
                self.env['stock.quant']._update_available_quantity(
                    target_product,
                    stock_location,
                    qty,
                    lot_id=child_lot
                )

                created_lots.append(child_lot_name)

        self.write({'inventory_processed': True})
        
        if created_lots:
            self.message_post(
                body=_("Child lots created: %s") % ', '.join(created_lots)
            )

        return True

    def _print_creation_report(self):
        """Print child lot creation report"""
        self.ensure_one()
        try:
            report = self.env.ref('custom_rsfp_module.action_report_child_lot_creation_detail')
            return report.report_action(self)
        except ValueError:
            # If report template not found, just return True to avoid errors
            _logger.warning("Child lot creation report template not found, skipping report generation")
            return True

    def action_reset_to_draft(self):
        """Reset to draft state"""
        for record in self:
            record.write({'state': 'draft'})
        return True

    def action_view_all_child_lots(self):
        """Action to view all child lots in list view"""
        self.ensure_one()
        
        if not self.child_lot_ids:
            raise UserError(_("No child lots have been created yet."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Child Lots from {self.name}',
            'res_model': 'stock.lot',
            'domain': [('id', 'in', self.child_lot_ids.ids)],
            'view_mode': 'tree,form',
            'target': 'current',
            'context': {
                'search_default_parent_lot': self.parent_lot_id.name,
                'create': False
            }
        }