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
        # stock_location = self.env.ref('stock.stock_location_stock')

        # FIXED: Get the actual location where parent lot exists instead of hardcoded stock location
        parent_stock_location = self._get_parent_lot_location()

        # NEW: Use sorting location for child lots (where sorting actually happens)
        sorting_location = self.sorting_location_id

        parent_lot_name = self.parent_lot_id.name
        created_lots = []

        # MINIMAL CHANGE: Just add DC to existing grades list
        # grades = [
        #     ('A', self.qty_grade_a, stock_location),
        #     ('B', self.qty_grade_b, stock_location),
        #     ('C', self.qty_grade_c, stock_location),
        #     ('DC', self.qty_grade_dc, waste_location)  # Only addition
        # ]

        # grades = [
        #     ('A', self.qty_grade_a, parent_stock_location),  # Use parent's location
        #     ('B', self.qty_grade_b, parent_stock_location),  # Use parent's location
        #     ('C', self.qty_grade_c, parent_stock_location),  # Use parent's location
        #     ('DC', self.qty_grade_dc, waste_location)  # Only DC goes to waste location
        # ]

        # Child lots A, B, C go to sorting location; DC goes to waste location
        grades = [
            ('A', self.qty_grade_a, sorting_location),      # Created where sorting happens
            ('B', self.qty_grade_b, sorting_location),      # Created where sorting happens
            ('C', self.qty_grade_c, sorting_location),      # Created where sorting happens
            ('DC', self.qty_grade_dc, waste_location)       # Discarded items go to waste
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
                # self.env['stock.quant']._update_available_quantity(
                #     self.product_id,
                #     stock_location,
                #     -qty,
                #     lot_id=self.parent_lot_id
                # )

                self.env['stock.quant']._update_available_quantity(
                    self.product_id,
                    parent_stock_location,  # Use the actual parent location, not hardcoded stock location
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
    
    def _get_parent_lot_location(self):
        """Get the location where parent lot inventory actually exists"""
        self.ensure_one()
        
        # Find where the parent lot has inventory
        quants = self.env['stock.quant'].search([
            ('lot_id', '=', self.parent_lot_id.id),
            ('quantity', '>', 0)
        ], limit=1)
        
        if quants:
            _logger.info(f"Parent lot {self.parent_lot_id.name} found in location: {quants.location_id.name}")
            return quants.location_id
        else:
            # Fallback to DS/Stock if it exists, otherwise stock location
            ds_stock = self.env['stock.location'].search([
                ('complete_name', 'ilike', 'DS/Stock'),
                ('usage', '=', 'internal')
            ], limit=1)
            
            if ds_stock:
                _logger.info(f"Using DS/Stock as fallback location")
                return ds_stock
            else:
                _logger.warning("No DS/Stock found, using default stock location")
                return self.env.ref('stock.stock_location_stock')

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

    







    # inventory fix (temporarily)

    # @api.model
    # def fix_wh_stock_negative_quantities(self):
    #     """Fix negative quantities in WH/Stock by transferring them to DS/Stock"""
    #     _logger.info("=== STARTING WH/STOCK NEGATIVE QUANTITY FIX ===")
        
    #     # Find WH/Stock location
    #     wh_stock = self.env['stock.location'].search([
    #         ('complete_name', 'ilike', 'WH/Stock'),
    #         ('usage', '=', 'internal')
    #     ], limit=1)
        
    #     if not wh_stock:
    #         _logger.warning("WH/Stock location not found, skipping fix")
    #         return {'fixed_count': 0, 'errors': []}
        
    #     # Find DS/Stock location
    #     ds_stock = self.env['stock.location'].search([
    #         ('complete_name', 'ilike', 'DS/Stock'),
    #         ('usage', '=', 'internal')
    #     ], limit=1)
        
    #     if not ds_stock:
    #         _logger.error("DS/Stock location not found, cannot proceed with fix")
    #         return {'fixed_count': 0, 'errors': ['DS/Stock location not found']}
        
    #     # Find all negative quantity records in WH/Stock
    #     negative_quants = self.env['stock.quant'].search([
    #         ('location_id', '=', wh_stock.id),
    #         ('quantity', '<', 0),
    #         ('lot_id', '!=', False)
    #     ])
        
    #     _logger.info(f"Found {len(negative_quants)} negative quantity records in WH/Stock")
        
    #     fixed_count = 0
    #     errors = []
        
    #     for quant in negative_quants:
    #         try:
    #             lot_name = quant.lot_id.name
    #             negative_qty = quant.quantity  # e.g., -20.00
    #             product = quant.product_id
                
    #             _logger.info(f"Fixing lot {lot_name}: transferring {negative_qty} from WH/Stock to DS/Stock")
                
    #             # STEP 1: Add the negative quantity to DS/Stock (this will reduce DS/Stock quantity)
    #             # If DS/Stock has +20.00 and we add -20.00, result will be 0.00
    #             self.env['stock.quant']._update_available_quantity(
    #                 product,
    #                 ds_stock,
    #                 negative_qty,  # Add the negative quantity (-20.00)
    #                 lot_id=quant.lot_id
    #             )
                
    #             # STEP 2: Remove the negative quantity from WH/Stock (make it zero)
    #             # If WH/Stock has -20.00 and we subtract -20.00, result will be 0.00
    #             self.env['stock.quant']._update_available_quantity(
    #                 product,
    #                 wh_stock,
    #                 -negative_qty,  # Subtract the negative (so -(-20.00) = +20.00)
    #                 lot_id=quant.lot_id
    #             )
                
    #             fixed_count += 1
    #             _logger.info(f"Successfully transferred negative quantity for lot {lot_name}")
                
    #         except Exception as e:
    #             error_msg = f"Failed to fix lot {quant.lot_id.name if quant.lot_id else 'unknown'}: {str(e)}"
    #             _logger.error(error_msg)
    #             errors.append(error_msg)
        
    #     _logger.info(f"=== FIX COMPLETE: {fixed_count} records fixed, {len(errors)} errors ===")
        
    #     return {
    #         'fixed_count': fixed_count,
    #         'errors': errors
    #     }

    # @api.model
    # def fix_all_sorting_inventory_mismatches(self):
    #     """Comprehensive fix for all sorting-related inventory mismatches"""
    #     _logger.info("=== STARTING COMPREHENSIVE INVENTORY MISMATCH FIX ===")
        
    #     # Step 1: Fix negative quantities in WH/Stock
    #     wh_fix_result = self.fix_wh_stock_negative_quantities()
        
    #     # Step 2: Fix any remaining mismatches for confirmed sorting reports
    #     confirmed_reports = self.search([
    #         ('state', '=', 'confirmed'),
    #         ('inventory_processed', '=', True)
    #     ])
        
    #     additional_fixes = 0
        
    #     for report in confirmed_reports:
    #         try:
    #             # Check if parent lot still has inventory records that should be zero
    #             parent_quants = self.env['stock.quant'].search([
    #                 ('lot_id', '=', report.parent_lot_id.id),
    #                 ('quantity', '!=', 0)
    #             ])
                
    #             if parent_quants:
    #                 total_qty = sum(parent_quants.mapped('quantity'))
                    
    #                 # If total is near zero (within 0.01), it's a rounding/mismatch issue
    #                 if abs(total_qty) < 0.01:
    #                     _logger.info(f"Zeroing out mismatched quantities for lot {report.parent_lot_id.name}")
                        
    #                     for quant in parent_quants:
    #                         quant.sudo().write({
    #                             'quantity': 0,
    #                             'reserved_quantity': 0
    #                         })
                        
    #                     additional_fixes += 1
                        
    #         except Exception as e:
    #             _logger.error(f"Failed to fix additional mismatch for report {report.name}: {e}")
        
    #     # Prepare summary
    #     total_fixed = wh_fix_result['fixed_count'] + additional_fixes
    #     all_errors = wh_fix_result['errors']
        
    #     _logger.info(f"=== COMPREHENSIVE FIX COMPLETE ===")
    #     _logger.info(f"Total records fixed: {total_fixed}")
    #     _logger.info(f"WH/Stock negative fixes: {wh_fix_result['fixed_count']}")
    #     _logger.info(f"Additional mismatch fixes: {additional_fixes}")
    #     _logger.info(f"Errors encountered: {len(all_errors)}")
        
    #     return {
    #         'total_fixed': total_fixed,
    #         'wh_stock_fixes': wh_fix_result['fixed_count'],
    #         'additional_fixes': additional_fixes,
    #         'errors': all_errors
    #     }

    # @api.model
    # def action_manual_inventory_fix(self):
    #     """Manual action to fix inventory mismatches (can be called from UI)"""
    #     fix_result = self.fix_all_sorting_inventory_mismatches()
        
    #     if fix_result['total_fixed'] > 0:
    #         message = f"Successfully fixed {fix_result['total_fixed']} inventory records:\n"
    #         message += f"• WH/Stock negative quantities: {fix_result['wh_stock_fixes']}\n"
    #         message += f"• Additional mismatches: {fix_result['additional_fixes']}"
            
    #         if fix_result['errors']:
    #             message += f"\n\nErrors encountered: {len(fix_result['errors'])}"
    #             for error in fix_result['errors'][:5]:  # Show first 5 errors
    #                 message += f"\n• {error}"
    #             if len(fix_result['errors']) > 5:
    #                 message += f"\n... and {len(fix_result['errors']) - 5} more errors"
                    
    #             notification_type = 'warning'
    #         else:
    #             notification_type = 'success'
    #     else:
    #         message = "No inventory mismatches found to fix."
    #         notification_type = 'info'
        
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'title': 'Inventory Mismatch Fix Complete',
    #             'message': message,
    #             'type': notification_type,
    #             'sticky': True,
    #         }
    #     }
    


    # @api.model
    # def test_inventory_fix_manual(self):
    #     """Test method to manually trigger the fix"""
    #     import logging
    #     _logger = logging.getLogger(__name__)
        
    #     _logger.info("=== MANUAL TEST OF INVENTORY FIX ===")
        
    #     # Test WH/Stock fix specifically
    #     result = self.fix_wh_stock_negative_quantities()
        
    #     _logger.info(f"Manual test result: {result}")
        
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'title': 'Manual Inventory Fix Test',
    #             'message': f"Fixed {result['fixed_count']} records. Check logs for details.",
    #             'type': 'success' if result['fixed_count'] > 0 else 'warning',
    #             'sticky': True,
    #         }
    #     }
    

    # @api.model
    # def debug_check_negative_quants(self):
    #     """Debug method to check current negative quantities"""
    #     import logging
    #     _logger = logging.getLogger(__name__)
        
    #     _logger.info("=== CHECKING NEGATIVE QUANTITIES ===")
        
    #     # Find WH/Stock location
    #     wh_stock = self.env['stock.location'].search([
    #         ('complete_name', 'ilike', 'WH/Stock'),
    #         ('usage', '=', 'internal')
    #     ])
        
    #     _logger.info(f"Found WH/Stock locations: {[loc.complete_name for loc in wh_stock]}")
        
    #     if wh_stock:
    #         # Find negative quantities
    #         negative_quants = self.env['stock.quant'].search([
    #             ('location_id', '=', wh_stock[0].id),
    #             ('quantity', '<', 0)
    #         ])
            
    #         _logger.info(f"Found {len(negative_quants)} negative quants in WH/Stock")
    #         for quant in negative_quants:
    #             _logger.info(f"  - Product: {quant.product_id.name}, Lot: {quant.lot_id.name if quant.lot_id else 'No lot'}, Qty: {quant.quantity}")
        
    #     # Find DS/Stock location
    #     ds_stock = self.env['stock.location'].search([
    #         ('complete_name', 'ilike', 'DS/Stock'),
    #         ('usage', '=', 'internal')
    #     ])
        
    #     _logger.info(f"Found DS/Stock locations: {[loc.complete_name for loc in ds_stock]}")
        
    #     if ds_stock:
    #         # Check DK-241225-0002 lot specifically
    #         dk_quants = self.env['stock.quant'].search([
    #             ('location_id', '=', ds_stock[0].id),
    #             ('lot_id.name', '=', 'DK-241225-0002')
    #         ])
            
    #         _logger.info(f"DK-241225-0002 in DS/Stock: {len(dk_quants)} records")
    #         for quant in dk_quants:
    #             _logger.info(f"  - Qty: {quant.quantity}")
        
        # return True




    
    # individual sorting report fix 

    def action_fix_parent_lot_inventory(self):
        """Fix inventory mismatch for this sorting report's parent lot only"""
        self.ensure_one()
        
        if not self.parent_lot_id:
            message = "No parent lot found to fix."
            self.message_post(body=_(message))
            raise UserError(_(message))
        
        _logger.info(f"=== FIXING INVENTORY FOR PARENT LOT: {self.parent_lot_id.name} ===")
        
        # Find WH/Stock and DS/Stock locations
        wh_stock = self.env['stock.location'].search([
            ('complete_name', 'ilike', 'WH/Stock'),
            ('usage', '=', 'internal')
        ], limit=1)
        
        ds_stock = self.env['stock.location'].search([
            ('complete_name', 'ilike', 'DS/Stock'),
            ('usage', '=', 'internal')
        ], limit=1)
        
        if not wh_stock:
            message = "WH/Stock location not found. Cannot proceed with fix."
            self.message_post(body=_(message))
            raise UserError(_(message))
            
        if not ds_stock:
            message = "DS/Stock location not found. Cannot proceed with fix."
            self.message_post(body=_(message))
            raise UserError(_(message))
        
        # Find negative quantities for this specific parent lot in WH/Stock
        negative_quants = self.env['stock.quant'].search([
            ('location_id', '=', wh_stock.id),
            ('lot_id', '=', self.parent_lot_id.id),
            ('quantity', '<', 0)
        ])
        
        if not negative_quants:
            message = f"No negative quantities found for lot {self.parent_lot_id.name} in WH/Stock."
            _logger.info(message)
            self.message_post(body=_(message))
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Issues Found',
                    'message': message,
                    'type': 'info',
                }
            }
        
        # Fix each negative quant for this lot
        fixed_details = []
        total_fixed_qty = 0
        
        for quant in negative_quants:
            try:
                negative_qty = quant.quantity  # e.g., -20.00
                product_name = quant.product_id.name
                
                _logger.info(f"Fixing: {product_name}, Qty: {negative_qty}")
                
                # STEP 1: Transfer negative quantity to DS/Stock (reduces DS/Stock quantity)
                self.env['stock.quant']._update_available_quantity(
                    quant.product_id,
                    ds_stock,
                    negative_qty,  # Add the negative quantity
                    lot_id=quant.lot_id
                )
                
                # STEP 2: Remove negative quantity from WH/Stock (makes it zero)
                self.env['stock.quant']._update_available_quantity(
                    quant.product_id,
                    wh_stock,
                    -negative_qty,  # Remove the negative
                    lot_id=quant.lot_id
                )
                
                fixed_details.append(f"• {product_name}: {abs(negative_qty)} units")
                total_fixed_qty += abs(negative_qty)
                
                _logger.info(f"Successfully fixed negative quantity for {product_name}")
                
            except Exception as e:
                error_msg = f"Failed to fix negative quantity for {quant.product_id.name}: {str(e)}"
                _logger.error(error_msg)
                self.message_post(body=_(f"❌ Error: {error_msg}"))
                raise UserError(_(error_msg))
        
        # Log success message in chatter
        success_message = _(
            "✅ Inventory Mismatch Fixed:\n"
            "Transferred negative quantities from WH/Stock to DS/Stock:\n%s\n"
            "Total quantity corrected: %.2f %s"
        ) % (
            '\n'.join(fixed_details),
            total_fixed_qty,
            self.parent_lot_id.product_uom_id.name
        )
        
        self.message_post(body=success_message)
        _logger.info(f"Fix completed for lot {self.parent_lot_id.name}: {len(negative_quants)} records fixed")
        
        # Show success notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Inventory Fix Completed',
                'message': f"Successfully fixed inventory mismatch for lot {self.parent_lot_id.name}. Check the record's messages for details.",
                'type': 'success',
            }
        }

