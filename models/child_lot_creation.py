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
        states={'confirmed': [('readonly', True)]},
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
        default=fields.Date.today,
        states={'confirmed': [('readonly', True)]}
    )
    
    creator_id = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        required=True,
        states={'confirmed': [('readonly', True)]}
    )

    # ADD THIS MISSING FIELD:
    creation_location_id = fields.Many2one(
        'stock.location',
        string='Creation Location',
        required=True,
        states={'confirmed': [('readonly', True)]},
        help="Default location for creating child lots"
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

    # NEW: Child Lot Lines (replacing Grade A/B/C)
    child_lot_lines = fields.One2many(
        'custom.child.lot.line',
        'creation_id',
        string='Child Lots to Create',
        states={'confirmed': [('readonly', True)]}
    )

    # Computed Fields
    qty_total_to_create = fields.Float(
        string='Total Quantity to Create',
        compute='_compute_total_to_create',
        store=True,
        help="Sum of all child lot quantities"
    )

    qty_available_remaining = fields.Float(
    string='Quantity Available',
    compute='_compute_qty_available_remaining',
    store=False,
    help="Remaining quantity available in source lot after assigning child lot quantities"
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

    notes = fields.Text(
        string='Creation Notes',
        states={'confirmed': [('readonly', True)]}
    )

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

    @api.depends('child_lot_lines.quantity')
    def _compute_total_to_create(self):
        """Compute total quantity to be created"""
        for record in self:
            record.qty_total_to_create = sum(line.quantity for line in record.child_lot_lines if line.quantity > 0)

    @api.depends('source_qty_total', 'child_lot_lines.quantity')
    def _compute_qty_available_remaining(self):
        """Compute remaining quantity available after assigning child lot quantities"""
        for record in self:
            total_assigned = sum(line.quantity for line in record.child_lot_lines if line.quantity > 0)
            record.qty_available_remaining = record.source_qty_total - total_assigned

    @api.depends('child_lot_lines.created_lot_id')
    def _compute_child_lot_ids(self):
        """Compute created child lots from lines"""
        for record in self:
            created_lots = record.child_lot_lines.mapped('created_lot_id')
            record.child_lot_ids = [(6, 0, created_lots.ids)]

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
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.child.lot.creation.daily') or _('New')
        return super().create(vals_list)

    @api.constrains('child_lot_lines')
    def _check_child_lot_quantities(self):
        """Validate child lot quantities"""
        for record in self:
            if record.state == 'confirmed':
                continue  # Skip validation for confirmed records
                
            if not record.child_lot_lines:
                continue  # Allow empty lines in draft
            
            # Check if any line has valid quantity
            valid_lines = record.child_lot_lines.filtered(lambda l: l.quantity > 0)
            if not valid_lines:
                continue  # Allow all-zero quantities in draft
            
            # Check total doesn't exceed source quantity
            source_qty = record.parent_lot_id.product_qty if record.parent_lot_id else 0.0
            if record.qty_total_to_create > source_qty:
                raise ValidationError(_(
                    "Total child lot quantities (%.2f) cannot exceed source lot quantity (%.2f)"
                ) % (record.qty_total_to_create, source_qty))

    def action_confirm(self):
        """Confirm the child lot creation and create child lots"""
        for record in self:
            record._validate_creation_data()
            # Store the source quantity BEFORE any processing
            record.source_qty_at_creation = record.parent_lot_id.product_qty
            record._create_child_lots_sequential()
            record.write({'state': 'confirmed'})
            record.message_post(
                body=_("Child Lot Creation confirmed by %s") % self.env.user.name
            )
        
        return self._print_creation_report()

    def _validate_creation_data(self):
        """Validate creation data before confirmation"""
        self.ensure_one()
        
        if not self.parent_lot_id:
            raise UserError(_("Source Lot is required."))

        # Check if we have any valid child lot lines
        valid_lines = self.child_lot_lines.filtered(lambda l: l.quantity > 0)
        if not valid_lines:
            raise UserError(_("At least one child lot with quantity > 0 is required."))

        # Use current source quantity for validation
        source_qty = self.parent_lot_id.product_qty or 0.0
        
        if source_qty <= 0:
            raise UserError(_("Source lot has no available quantity."))
        
        if self.qty_total_to_create > source_qty:
            raise UserError(_(
                "Total child lot quantities (%.2f) cannot exceed source lot quantity (%.2f)"
            ) % (self.qty_total_to_create, source_qty))

        # Check all lines have locations
        for line in valid_lines:
            if not line.location_id:
                raise UserError(_("Location is required for all child lot lines."))

    def _create_child_lots_sequential(self):
        """Create child lots with sequential naming"""
        self.ensure_one()
        
        if self.inventory_processed:
            return True

        parent_lot_name = self.parent_lot_id.name
        created_lots = []
        
        # Find the next sequential number
        next_number = self._get_next_sequence_number()
        
        # Process each valid line
        valid_lines = self.child_lot_lines.filtered(lambda l: l.quantity > 0)
        
        for line in valid_lines:
            # Generate sequential child lot name
            child_lot_name = f"{parent_lot_name}-{next_number}"
            
            # Use same product as parent lot (graded product)
            target_product = self.product_id

            # Create child lot with arrived_quantity context
            child_lot = self.env['stock.lot'].with_context(
                arrived_quantity=line.quantity
            ).create({
                'name': child_lot_name,
                'product_id': target_product.id,
                'ref': self.root_parent_lot_id.name if self.root_parent_lot_id else parent_lot_name,
                'parent_lot_id': self.parent_lot_id.id
            })

            # Add inventory for child lot
            self.env['stock.quant']._update_available_quantity(
                target_product,
                line.location_id,
                line.quantity,
                lot_id=child_lot
            )
            
            # IMPORTANT: Reduce parent lot quantity
            parent_location = self._get_parent_lot_location()
            self.env['stock.quant']._update_available_quantity(
                self.parent_lot_id.product_id,
                parent_location,
                -line.quantity,
                lot_id=self.parent_lot_id
            )

            # Update line with created lot
            line.created_lot_id = child_lot.id

            created_lots.append(child_lot_name)
            next_number += 1  # Increment for next lot

        self.write({'inventory_processed': True})
        
        if created_lots:
            self.message_post(
                body=_("Child lots created: %s (Parent lot quantity reduced accordingly)") % ', '.join(created_lots)
            )

        return True

    def _get_next_sequence_number(self):
        """Get the next sequential number for child lots"""
        self.ensure_one()
        
        parent_lot_name = self.parent_lot_id.name
        
        # Find existing child lots with pattern: parent_name-NUMBER
        existing_lots = self.env['stock.lot'].search([
            ('name', 'like', f"{parent_lot_name}-%"),
            ('parent_lot_id', '=', self.parent_lot_id.id)
        ])
        
        max_number = 0
        pattern_prefix = f"{parent_lot_name}-"
        
        for lot in existing_lots:
            if lot.name.startswith(pattern_prefix):
                # Extract the number after the last hyphen
                suffix = lot.name[len(pattern_prefix):]
                # Handle multi-level: A-1-2 -> get the first number after parent name
                if '-' in suffix:
                    # This is a grandchild (e.g., DM-171125-0001-A-1-2)
                    # We want the first number (1 in this case)
                    try:
                        first_number = int(suffix.split('-')[0])
                        max_number = max(max_number, first_number)
                    except ValueError:
                        continue
                else:
                    # This is a direct child (e.g., DM-171125-0001-A-1)
                    try:
                        number = int(suffix)
                        max_number = max(max_number, number)
                    except ValueError:
                        continue
        
        return max_number + 1

    def _get_parent_lot_location(self):
        """Get the location where parent lot inventory exists"""
        self.ensure_one()
        
        # Find where the parent lot has inventory
        quants = self.env['stock.quant'].search([
            ('lot_id', '=', self.parent_lot_id.id),
            ('quantity', '>', 0)
        ], limit=1)
        
        if quants:
            return quants.location_id
        else:
            # Fallback to stock location
            return self.env.ref('stock.stock_location_stock')

    def _print_creation_report(self):
        """Print child lot creation report"""
        self.ensure_one()
        try:
            report = self.env.ref('custom_rsfp_module.action_report_child_lot_creation_detail')
            return report.report_action(self)
        except ValueError:
            _logger.warning("Child lot creation report template not found, skipping report generation")
            return True

    def action_reset_to_draft(self):
        """Reset to draft state (only if no child lots created)"""
        for record in self:
            if record.inventory_processed:
                raise UserError(_("Cannot reset to draft: Child lots have already been created. Please create a new record instead."))
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

    def action_add_empty_line(self):
        """Add an empty line to the child lot lines"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Cannot add lines to confirmed records."))
        
        # Get default location
        default_location = self.env.ref('stock.stock_location_stock', raise_if_not_found=False)
        if self.parent_lot_id:
            quants = self.env['stock.quant'].search([
                ('lot_id', '=', self.parent_lot_id.id),
                ('quantity', '>', 0)
            ], limit=1)
            if quants:
                default_location = quants.location_id

        # Add new line
        self.env['custom.child.lot.line'].create({
            'creation_id': self.id,
            'sequence': len(self.child_lot_lines) * 10 + 10,
            'quantity': 0.0,
            'location_id': default_location.id if default_location else False,
            'notes': ''
        })
        
        return True

    @api.onchange('parent_lot_id')
    def _onchange_parent_lot_id(self):
        """When parent lot changes, add one empty line if no lines exist"""
        if self.parent_lot_id and not self.child_lot_lines:
            # Get default location from parent lot
            default_location = self.env.ref('stock.stock_location_stock', raise_if_not_found=False)
            quants = self.env['stock.quant'].search([
                ('lot_id', '=', self.parent_lot_id.id),
                ('quantity', '>', 0)
            ], limit=1)
            if quants:
                default_location = quants.location_id
            
            # Create initial empty line
            self.child_lot_lines = [(0, 0, {
                'sequence': 10,
                'quantity': 0.0,
                'location_id': default_location.id if default_location else False,
                'notes': ''
            })]