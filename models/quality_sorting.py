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

    # FIXED: Simple Many2one field without complex domain
    parent_lot_id = fields.Many2one(
        'stock.lot',
        string='Parent Lot/Batch',
        required=True,
        help="Select the parent lot/batch to be sorted into grades"
    )
    
    # FIXED: Compute method that finds purchase order from stock moves
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

    # FIXED: Store parent quantity at time of sorting (before any reductions), Make parent_qty_total non-stored to avoid database issues
    parent_qty_total = fields.Float(
        string='Parent Lot Total Quantity',
        compute='_compute_parent_qty_total',
        store=False,  # Changed from True to False
        readonly=True,
        help="Total quantity available in the parent lot"
    )

    # NEW: Store the original parent quantity for reporting
    parent_qty_at_sorting = fields.Float(
        string='Parent Quantity at Sorting',
        readonly=True,
        help="Original parent lot quantity when sorting was performed"
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
    
    qty_grade_dc = fields.Float(
        string='Discarded Qty',
        digits='Product Unit of Measure',
        default=0.0,
        help="Quantity that has been discarded/rejected during sorting"
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

    # Created Child Lots (for display as copyable text)
    child_lot_names = fields.Char(
    string='Child Lot Names',
    compute='_compute_child_lot_names',
    help="Comma-separated child lot names for easy copying"
)

    notes = fields.Text(string='Sorting Notes')

    # FIXED: Enhanced compute method for purchase_order_id
    @api.depends('parent_lot_id')
    def _compute_purchase_order(self):
        """Compute purchase order from parent lot's stock moves"""
        for record in self:
            if not record.parent_lot_id:
                record.purchase_order_id = False
                continue
            
            _logger.info(f"Computing purchase order for lot: {record.parent_lot_id.name}")
            
            # Method 1: Find through stock move lines (most reliable)
            move_lines = self.env['stock.move.line'].search([
                ('lot_id', '=', record.parent_lot_id.id),
                ('state', '=', 'done'),
                ('move_id.purchase_line_id', '!=', False)
            ], limit=1)
            
            if move_lines and move_lines.move_id.purchase_line_id:
                record.purchase_order_id = move_lines.move_id.purchase_line_id.order_id
                _logger.info(f"Found PO via move lines: {record.purchase_order_id.name}")
                continue
            
            # Method 2: Find through stock moves directly
            moves = self.env['stock.move'].search([
                ('move_line_ids.lot_id', '=', record.parent_lot_id.id),
                ('state', '=', 'done'),
                ('purchase_line_id', '!=', False)
            ], limit=1)
            
            if moves and moves.purchase_line_id:
                record.purchase_order_id = moves.purchase_line_id.order_id
                _logger.info(f"Found PO via moves: {record.purchase_order_id.name}")
                continue
            
            # Method 3: Search by product and date (fallback)
            recent_pos = self.env['purchase.order'].search([
                ('order_line.product_id', '=', record.parent_lot_id.product_id.id),
                ('state', 'in', ['purchase', 'done']),
                ('date_order', '<=', fields.Datetime.now())
            ], order='date_order desc', limit=5)
            
            for po in recent_pos:
                # Check if this PO has any pickings with our lot
                po_pickings = po.picking_ids.filtered(lambda p: p.state == 'done')
                po_lots = po_pickings.mapped('move_line_ids.lot_id')
                if record.parent_lot_id in po_lots:
                    record.purchase_order_id = po
                    _logger.info(f"Found PO via fallback method: {po.name}")
                    break
            else:
                record.purchase_order_id = False
                _logger.info("No purchase order found for lot")



    # NEW: Compute method for parent_qty_total
    @api.depends('parent_lot_id', 'parent_qty_at_sorting', 'state')
    def _compute_parent_qty_total(self):
        """Compute the total quantity of the parent lot"""
        for record in self:
            if not record.parent_lot_id:
                record.parent_qty_total = 0.0
                continue
            
            # If confirmed, use the stored quantity from sorting time
            if record.state == 'confirmed' and record.parent_qty_at_sorting:
                record.parent_qty_total = record.parent_qty_at_sorting
            else:
                # For draft records, use current lot quantity
                record.parent_qty_total = record.parent_lot_id.product_qty or 0.0

    @api.depends('qty_grade_a', 'qty_grade_b', 'qty_grade_c', 'qty_grade_dc')
    def _compute_total_sorted(self):
        for record in self:
            record.qty_total_sorted = (record.qty_grade_a + record.qty_grade_b + 
                                     record.qty_grade_c + record.qty_grade_dc)

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                # Use the new daily sequence
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.sorting.report.daily') or _('New')
        return super().create(vals_list)

    # FIXED: Temporarily disable constraint during module update
    @api.constrains('qty_grade_a', 'qty_grade_b', 'qty_grade_c', 'qty_grade_dc', 'parent_qty_total')
    def _check_sorting_quantities(self):
        # Skip validation during module installation/update
        if self.env.context.get('module_uninstall') or self.env.context.get('install_mode'):
            return
        
        for record in self:
            # Compute parent quantity on the fly for validation
            parent_qty = record.parent_lot_id.product_qty if record.parent_lot_id else 0.0
            total_sorted = (record.qty_grade_a + record.qty_grade_b + 
                          record.qty_grade_c + record.qty_grade_dc)
            
            if total_sorted > parent_qty:
                raise ValidationError(_(
                    "Total sorted quantity (%.2f) cannot exceed parent lot quantity (%.2f)"
                ) % (total_sorted, parent_qty))

    def action_confirm(self):
        """Confirm the sorting report and create child lots"""
        for record in self:
            # IMPORTANT: Store the parent quantity BEFORE any processing
            record.parent_qty_at_sorting = record.parent_lot_id.product_qty
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

        # Use current parent quantity for validation
        parent_qty = self.parent_lot_id.product_qty or 0.0
        
        if parent_qty <= 0:
            raise UserError(_("Parent lot has no available quantity."))
        
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

        # Get existing waste location or create if needed
        waste_location = self._get_or_create_waste_location()
        stock_location = self.env.ref('stock.stock_location_stock')
        parent_lot_name = self.parent_lot_id.name
        created_lots = []

        # MINIMAL CHANGE: Just add DC to existing grades list
        grades = [
            ('A', self.qty_grade_a, stock_location),
            ('B', self.qty_grade_b, stock_location),
            ('C', self.qty_grade_c, stock_location),
            ('DC', self.qty_grade_dc, waste_location)  # Only addition
        ]

        # Rest of the method stays exactly the same
        for grade_letter, qty, target_location in grades:
            if qty > 0:
                child_lot_name = f"{parent_lot_name}-{grade_letter}"
                
                # Use existing method for A,B,C or new method for DC
                if grade_letter == 'DC':
                    graded_product = self._get_discarded_product()
                else:
                    graded_product = self._get_graded_product(grade_letter)
                
                # Create child lot with arrived_quantity context
                child_lot = self.env['stock.lot'].with_context(
                    arrived_quantity=qty
                ).create({
                    'name': child_lot_name,
                    'product_id': graded_product.id,
                    'ref': parent_lot_name,
                    'parent_lot_id': self.parent_lot_id.id
                })

                # Update inventory  Only ADD inventory for child lots, don't reduce parent
                self.env['stock.quant']._update_available_quantity(
                    graded_product,
                    target_location,
                    qty,
                    lot_id=child_lot
                )

                # if want to convert the process in which the parent lot quantity also has to be reduced after sorting, just uncomment the below code. 
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
                body=_("Child lots created: %s (Parent lot quantity reduced)") % ', '.join(created_lots)
            )

        return True

    def _get_graded_product(self, grade_letter):
        """Get the graded product for a specific grade"""
        if not self.product_id:
            return False
            
        base_name = self.product_id.name.replace(' - Bulk', '').replace('Bulk', '')
        
        # Try different search patterns
        search_patterns = [
            f'{base_name} - Grade {grade_letter}',
            f'{base_name} Grade {grade_letter}',
            f'Grade {grade_letter} {base_name}',
        ]
        
        for pattern in search_patterns:
            graded_product = self.env['product.product'].search([
                ('name', 'ilike', pattern),
                ('tracking', '=', 'lot')
            ], limit=1)
            
            if graded_product:
                _logger.info(f"Found graded product: {graded_product.name} for grade {grade_letter}")
                return graded_product
        
        # Fallback: search more broadly
        graded_product = self.env['product.product'].search([
            ('name', 'ilike', base_name),
            ('name', 'ilike', f'grade {grade_letter}'),
            ('tracking', '=', 'lot')
        ], limit=1)
        
        if graded_product:
            _logger.info(f"Found graded product (fallback): {graded_product.name}")
        else:
            _logger.warning(f"No graded product found for base name: {base_name}, grade: {grade_letter}")
        
        return graded_product

    def _get_or_create_waste_location(self):
        """Get or create waste/discarded location"""
        waste_location = self.env['stock.location'].search([
            ('name', 'ilike', 'waste'),
            ('usage', '=', 'internal')
        ], limit=1)
        
        if not waste_location:
            parent_location = self.env.ref('stock.stock_location_locations', raise_if_not_found=False)
            if not parent_location:
                parent_location = self.env.ref('stock.stock_location_stock')
            
            waste_location = self.env['stock.location'].create({
                'name': 'Waste/Discarded',
                'usage': 'internal',
                'location_id': parent_location.id,
                'company_id': self.env.company.id
            })
        
        return waste_location

    def _get_discarded_product(self):
        """Get or create the discarded product for the current bulk product"""
        if not self.product_id:
            return False
            
        base_name = self.product_id.name.replace(' - Bulk', '').replace('Bulk', '').strip()
        discarded_name = f'{base_name} - Discarded'
        
        discarded_product = self.env['product.product'].search([
            ('name', '=', discarded_name),
            ('tracking', '=', 'lot')
        ], limit=1)
        
        if not discarded_product:
            discarded_product = self.env['product.product'].create({
                'name': discarded_name,
                'type': 'product',
                'tracking': 'lot',
                'categ_id': self.product_id.categ_id.id,
                'uom_id': self.product_id.uom_id.id,
                'uom_po_id': self.product_id.uom_po_id.id,
                'standard_price': 0.0,
                'list_price': 0.0,
                # 'lot_abbreviation': self.product_id.lot_abbreviation or 'DC',
                'active': True
            })
        
        return discarded_product

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
    
    def action_view_child_lot(self):
        """Action to view a specific child lot"""
        lot_id = self.env.context.get('lot_id')
        if not lot_id:
            raise UserError(_("No lot specified"))
        
        lot = self.env['stock.lot'].browse(lot_id)
        if not lot.exists():
            raise UserError(_("Lot not found"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Child Lot: {lot.name}',
            'res_model': 'stock.lot',
            'res_id': lot.id,
            'view_mode': 'form',
            'target': 'new',  # Opens in popup
            'context': {'create': False, 'edit': False}  # Read-only
        }

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
    
    @api.depends('child_lot_ids')
    def _compute_child_lot_names(self):
        """Compute comma-separated child lot names for copying"""
        for record in self:
            if record.child_lot_ids:
                record.child_lot_names = ', '.join(record.child_lot_ids.mapped('name'))
            else:
                record.child_lot_names = ''