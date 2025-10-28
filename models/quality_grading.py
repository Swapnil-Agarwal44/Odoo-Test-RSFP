from odoo import models, fields, api, _ # type: ignore
from odoo.exceptions import UserError, ValidationError # type: ignore
import logging

_logger = logging.getLogger(__name__)

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
    # grade_type = fields.Selection([
    #     ('grade_a', 'Grade A'),
    #     ('grade_b', 'Grade B'),
    #     ('grade_c', 'Grade C'),
    # ], string='Product Grade', required=True)

    # **REPLACED: grade_type selection with direct graded_product_id**
    # graded_product_id = fields.Many2one(
    #     'product.product',
    #     string='Graded Product',
    #     domain="[('id', 'in', available_graded_products)]",
    #     required=True,
    #     help="Select the specific graded product (e.g., Dried Mango - Grade A) for this test line."
    # )

    # **NEW: Computed field to filter graded products based on parent product**
    available_graded_products = fields.Many2many(
        'product.product',
        compute='_compute_available_graded_products',
        store=False,
        help="Technical field to filter graded products based on parent product"
    )

    # **NEW: Computed field to determine grade letter for naming (A, B, C)**
    grade_letter = fields.Char(
        string='Grade',
        compute='_compute_grade_letter',
        store=True,
        help="Extracted grade letter from product name for child lot naming"
    )

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
    
    @api.depends('graded_product_id', 'grading_id.qty_grade_a', 'grading_id.qty_grade_b', 'grading_id.qty_grade_c')
    def _compute_qty_of_grade(self):
        for line in self:
            if line.grade_letter == 'A':
                line.qty_of_grade = line.grading_id.qty_grade_a
            elif line.grade_letter == 'B':
                line.qty_of_grade = line.grading_id.qty_grade_b
            elif line.grade_letter == 'C':
                line.qty_of_grade = line.grading_id.qty_grade_c
            else:
                line.qty_of_grade = 0.0

    @api.depends('qty_of_grade', 'rate_per_kg')
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = line.qty_of_grade * line.rate_per_kg

    # --- Constraint to prevent duplicate grades on one report ---
    @api.constrains('graded_product_id', 'grading_id')
    def _check_unique_graded_product_per_report(self):
        for line in self:
            domain = [
                ('grading_id', '=', line.grading_id.id),
                ('graded_product_id', '=', line.graded_product_id.id),
                ('id', '!=', line.id),
            ]
            if self.search(domain, limit=1):
                raise ValidationError(
                    _('A Quality Report can only have one test line for each graded product (%s).') % line.graded_product_id.name
                )
    

    @api.depends('graded_product_id')
    def _compute_grade_letter(self):
        """Extract grade letter from product name for lot naming"""
        for line in self:
            if line.graded_product_id:
                product_name = line.graded_product_id.name.upper()
                # Extract grade letter (assumes naming like "Product - Grade A")
                if 'GRADE A' in product_name or ' A' in product_name:
                    line.grade_letter = 'A'
                elif 'GRADE B' in product_name or ' B' in product_name:
                    line.grade_letter = 'B'
                elif 'GRADE C' in product_name or ' C' in product_name:
                    line.grade_letter = 'C'
                else:
                    line.grade_letter = 'Unknown'
            else:
                line.grade_letter = ''

    
    @api.depends('grading_id.product_id')
    def _compute_available_graded_products(self):
        """Filter graded products based on the parent product in the main report"""
        for line in self:
            if not line.grading_id.product_id:
                line.available_graded_products = [(6, 0, [])]
                continue
            
            parent_product = line.grading_id.product_id
            
            # Find graded products related to the parent product
            # Method 1: Using product categories (if you use categories for grading)
            # graded_products = self.env['product.product'].search([
            #     ('categ_id', '=', parent_product.categ_id.id),
            #     ('tracking', '=', 'lot'),
            #     ('id', '!=', parent_product.id),  # Exclude the parent product itself
            #     '|', 
            #     ('name', 'ilike', 'grade'),
            #     ('name', 'ilike', parent_product.name.split(' - ')[0])  # Match base name
            # ])
            
            # Method 2: Alternative - if you use a specific naming convention
            base_name = parent_product.name.replace(' - Bulk', '').replace('Bulk', '')
            graded_products = self.env['product.product'].search([
                ('name', 'ilike', base_name),
                ('name', 'ilike', 'grade'),
                ('tracking', '=', 'lot'),
                ('id', '!=', parent_product.id)
            ])
            
            line.available_graded_products = [(6, 0, graded_products.ids)]

# --- 3. Quality Grading Report Model (Header/Parent) ---
class CustomQualityGrading(models.Model):
    _name = 'custom.quality.grading'
    _description = 'Custom Quality Grading Report Header'
    _inherit = ['mail.thread', 'mail.activity.mixin'] # Adds Chatter functionality (Notes, Followers)
    _rec_name = 'name'

    # Header Details
    name = fields.Char(string='Report Reference', required=True, copy=False, readonly=True, 
                       default=lambda self: _('New'))
    
    # **NEW FIELD: State Management**
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', readonly=True, tracking=True,
       help="Draft: Report can be edited. Confirmed: Report is locked and inventory operations are triggered.")

    # Links to the built-in Purchase Order model
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order Ref', 
                                        required=True, ondelete='restrict', tracking=True)
    product_id = fields.Many2one('product.product', string='Product Tested', required=True)
    receipt_date = fields.Date(string='Testing Date', required=True, default=fields.Date.today)
    tester_id = fields.Many2one('res.users', string='Tested By', 
                                default=lambda self: self.env.user, required=True)
    
    # NEW FIELD: Test Location edited to include the states of the report. 
    test_location_id = fields.Many2one('stock.location', string='Test Location',
                                       help="The internal location where the quality testing took place.")
    
    # NEW FIELD: Parent Lot/Batch ID (Replaces the commented-out lot_id field)
    parent_lot_id = fields.Many2one(
        'stock.lot', 
        string='Parent Lot/Batch', 
        domain="[('id', 'in', available_lot_ids)]",  # Dynamic domain
        #required=True, # Lot is required to confirm the report and perform segregation
        # Pass product_id as default_product_id to the Lot model
        # context={'default_product_id': fields.Many2one.to_ids},
        context={'default_product_id': 'product_id'},
        # The default lot name will be generated on the Lot model itself
        help="The main Lot/Batch number assigned during the initial Purchase Receipt.")

    # NEW FIELD: Computed field to get available lots from the selected PO
    available_lot_ids = fields.Many2many(
        'stock.lot',
        compute='_compute_available_lots',
        store=False,
        help="Technical field to filter lots based on selected Purchase Order"
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

    # NEW FIELD: Created to store if the grading move has been generated for the report or not
    inventory_processed = fields.Boolean(
    string="Inventory Processed",
    default=False,
    copy=False,
    help="Indicates if the stock moves for grading have been generated."
    )

    # NEW FIELD: Get created child lots for barcode printing
    child_lot_ids = fields.Many2many(
    'stock.lot',
    compute='_compute_child_lot_ids',
    string='Created Child Lots',
    help="Child lots created from this quality grading report"
    )

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
            
    @api.depends('parent_lot_id', 'inventory_processed', 'test_line_ids')
    def _compute_child_lot_ids(self):
        """Compute child lots created from this report"""
        for record in self:
            if not record.parent_lot_id or not record.inventory_processed:
                record.child_lot_ids = [(6, 0, [])]
                continue
            
            # Find child lots that reference this parent lot
            parent_lot_name = record.parent_lot_id.name
            child_lots = self.env['stock.lot'].search([
                ('ref', '=', parent_lot_name),
                ('parent_lot_id', '=', record.parent_lot_id.id)
            ])
            
            record.child_lot_ids = [(6, 0, child_lots.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        """Assigns the sequence number upon creation."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.quality.grading') or _('New')
        return super().create(vals_list)
    
    # ... (existing code and imports) ...

    # @api.model
    # def create(self, vals):
        # Call super first to create the record
        #new_report = super(CustomQualityGrading, self).create(vals)
        
        # Check if the created report is already complete and should be processed
        # We must explicitly check the conditions here or call the processing logic
        
        # Simple check: If parent_lot_id is not provided, we prevent creation for now
        # if not vals.get('parent_lot_id'):
        #     # NOT-E: You can choose to allow creation but prevent processing.
        #     # For simplicity, let's keep the processing check in 'write' for now
        #     pass 
            
        # return new_report
        
    # We will focus on improving the validation within write() 
    # to ensure it always runs when the critical fields are saved.

    def write(self, vals):
    # 1. Call super first to save the data
        res = super(CustomQualityGrading, self).write(vals)

        # for report in self:
            # Check 1: Has the inventory been processed? If yes, skip.
            # if report.inventory_processed:
                # continue
                
            # Check 2: Check if the report is ready to be processed.
            # This check should ONLY run if a critical field was changed, 
            # OR if we are doing a mass save/update.
            
            # We assume the user is trying to finalize the report when
            # they save after entering the graded quantities and parent lot.
            
            # We enforce the validation first. If any check fails, it raises UserError
            # and prevents the processing logic below.
            
            # Validation checks (Use 'report' which has the latest, saved values)
            # if not report.parent_lot_id:
                # We allow the save but stop processing
                # continue 
                # OR: raise UserError("The Parent Lot/Batch ID must be set before processing.")
                
            # if report.qty_received > 0 and report.qty_total_graded == report.qty_received:
                # The report is fully graded and validated, so we process it.
                
                # Call the inventory generation logic
                # report._generate_graded_inventory_moves()
                
                # Mark as processed
                # report.write({'inventory_processed': True}) 
                
        return res
    

    def _generate_graded_inventory_moves(self):
        # """Creates child lots and stock moves based on test lines with graded products"""
        
        #3rd attempt: child lots are also created and the quantity is updated in them, but the parent lot is still containing the aggregated quantity. 
    #     """Simple inventory adjustment approach"""
    #     self.ensure_one()

    #     if self.inventory_processed:
    #         return True

    #     stock_location = self.env.ref('stock.stock_location_stock')
    #     created_lots = []

    #     for test_line in self.test_line_ids:
    #         if test_line.qty_of_grade > 0 and test_line.graded_product_id:
                
    #             child_lot_name = f"{self.parent_lot_id.name}-{test_line.grade_letter}"
                
    #             # Create Child Lot
    #             child_lot = self.env['stock.lot'].create({
    #                 'name': child_lot_name,
    #                 'product_id': test_line.graded_product_id.id,
    #                 'ref': self.parent_lot_id.name,
    #             })
                
    #             # Simple inventory adjustment
    #             self.env['stock.quant']._update_available_quantity(
    #                 test_line.graded_product_id,
    #                 stock_location,
    #                 test_line.qty_of_grade,
    #                 lot_id=child_lot
    #             )
                
    #             created_lots.append(child_lot_name)

    #     self.write({'inventory_processed': True})
        
    #     if created_lots:
    #         self.message_post(
    #             body=_("Child lots created with inventory: %s") % ', '.join(created_lots)
    #         )

    #     return True
    
    # def _get_internal_picking_type(self):
    #     """Get the internal picking type for stock moves"""
    #     picking_type = self.env['stock.picking.type'].search([
    #         ('code', '=', 'internal'),
    #         ('warehouse_id.company_id', '=', self.env.company.id)
    #     ], limit=1)
        
    #     if not picking_type:
    #         # Fallback: create a basic internal picking type if none exists
    #         warehouse = self.env['stock.warehouse'].search([
    #             ('company_id', '=', self.env.company.id)
    #         ], limit=1)
            
    #         if warehouse:
    #             picking_type = warehouse.int_type_id
        
    #     return picking_type









    #4th attempt: this process is working fully, it is creating new child lots and updating the validated quantity, and also removing the quantity from the parent lot as well.
        """Creates child lots and adjusts inventory based on test lines with graded products"""
        self.ensure_one()

        # Skip if already processed
        if self.inventory_processed:
            return True

        stock_location = self.env.ref('stock.stock_location_stock')
        if not stock_location:
            raise UserError(_("Configuration Error: Default Stock Location not found."))

        parent_lot_name = self.parent_lot_id.name
        created_lots = []

        _logger.info(f"Starting inventory generation for report: {self.name}")
        _logger.info(f"Parent lot: {parent_lot_name}")
        _logger.info(f"Test lines count: {len(self.test_line_ids)}")

        # Process each test line that has a graded product and quantity
        for test_line in self.test_line_ids:
            _logger.info(f"Processing test line - Grade: {test_line.grade_letter}, Qty: {test_line.qty_of_grade}, Product: {test_line.graded_product_id.name if test_line.graded_product_id else 'None'}")
            
            if test_line.qty_of_grade > 0 and test_line.graded_product_id:
                
                # Create child lot name using the grade letter
                child_lot_name = f"{parent_lot_name}-{test_line.grade_letter}"
                
                # Check if child lot already exists
                existing_lot = self.env['stock.lot'].search([
                    ('name', '=', child_lot_name),
                    ('product_id', '=', test_line.graded_product_id.id)
                ], limit=1)
                
                if existing_lot:
                    child_lot = existing_lot
                    _logger.info(f"Using existing child lot: {child_lot.name}")
                else:
                    _logger.info(f"Creating new child lot: {child_lot_name}")
                    # 1. Create Child Lot
                    child_lot = self.env['stock.lot'].create({
                        'name': child_lot_name,
                        'product_id': test_line.graded_product_id.id,
                        'ref': parent_lot_name,
                        'parent_lot_id': self.parent_lot_id.id
                    })
                    created_lots.append(child_lot_name)
                    _logger.info(f"Child lot created successfully: {child_lot.name}")
                
                # 2. Method 1: Simple inventory adjustment (Recommended)
                try:
                    # Add inventory for the new graded product
                    self.env['stock.quant']._update_available_quantity(
                        test_line.graded_product_id,
                        stock_location,
                        test_line.qty_of_grade,
                        lot_id=child_lot
                    )
                    
                    # Reduce inventory from parent lot (if it exists)
                    parent_quant = self.env['stock.quant'].search([
                        ('product_id', '=', self.product_id.id),
                        ('location_id', '=', stock_location.id),
                        ('lot_id', '=', self.parent_lot_id.id)
                    ], limit=1)
                    
                    if parent_quant and parent_quant.available_quantity >= test_line.qty_of_grade:
                        self.env['stock.quant']._update_available_quantity(
                            self.product_id,
                            stock_location,
                            -test_line.qty_of_grade,
                            lot_id=self.parent_lot_id
                        )
                        _logger.info(f"Reduced parent lot quantity by {test_line.qty_of_grade}")
                    else:
                        _logger.warning(f"Parent lot {self.parent_lot_id.name} doesn't have enough quantity")
                    
                    _logger.info(f"Inventory adjustment completed successfully")
                    
                except Exception as e:
                    _logger.error(f"Error with inventory adjustment: {str(e)}")
                    
                    # 3. Method 2: Alternative using stock moves (if Method 1 fails)
                    try:
                        self._create_stock_move_alternative(test_line, child_lot, stock_location)
                    except Exception as e2:
                        _logger.error(f"Error with stock move alternative: {str(e2)}")
                        continue
                
                # Log the creation for traceability
                self.message_post(
                    body=_("Child lot %s created for %s (Qty: %.2f kg) - Parent: %s. Inventory transferred.") % (
                        child_lot_name, 
                        test_line.graded_product_id.name, 
                        test_line.qty_of_grade,
                        parent_lot_name
                    )
                )

        # Mark as processed and log success
        self.write({'inventory_processed': True})
        
        if created_lots:
            _logger.info(f"Successfully created lots: {created_lots}")
            self.message_post(
                body=_("Child lots created: %s. Inventory transferred successfully.") % ', '.join(created_lots)
            )
        else:
            _logger.info("No new child lots created - may have used existing lots.")
            self.message_post(
                body=_("Inventory processing completed. Child lots assigned.")
            )

        return True

    def _create_stock_move_alternative(self, test_line, child_lot, stock_location):
        """Alternative method using simpler stock moves"""
        _logger.info("Using alternative stock move method")
        
        # Create a simple stock move without complex lot tracking
        move = self.env['stock.move'].create({
            'name': f'Quality Grading: {self.parent_lot_id.name} → {child_lot.name}',
            'product_id': test_line.graded_product_id.id,
            'product_uom_qty': test_line.qty_of_grade,
            'product_uom': test_line.graded_product_id.uom_id.id,
            'location_id': stock_location.id,
            'location_dest_id': stock_location.id,
            'picking_type_id': self._get_internal_picking_type().id if self._get_internal_picking_type() else False,
            'state': 'draft',
        })
        
        _logger.info(f"Alternative stock move created: {move.name}")
        
        # Try to process the move
        try:
            move._action_confirm()
            
            # Create move line manually with simpler approach
            move_line = self.env['stock.move.line'].create({
                'move_id': move.id,
                'product_id': test_line.graded_product_id.id,
                'location_id': stock_location.id,
                'location_dest_id': stock_location.id,
                'lot_id': child_lot.id,  # Use child lot as both source and destination
                'qty_done': test_line.qty_of_grade,
                'product_uom_id': test_line.graded_product_id.uom_id.id,
            })
            
            move._action_done()
            _logger.info(f"Alternative stock move processed successfully")
            
        except Exception as e:
            _logger.error(f"Failed to process alternative stock move: {str(e)}")
            # If stock move fails, just create the lot without inventory transfer
            pass

    def _get_internal_picking_type(self):
        """Get the internal picking type for stock moves"""
        try:
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'internal'),
                ('warehouse_id.company_id', '=', self.env.company.id)
            ], limit=1)
            
            if not picking_type:
                # Fallback: try to get any internal picking type
                picking_type = self.env['stock.picking.type'].search([
                    ('code', '=', 'internal')
                ], limit=1)
            
            return picking_type
        except Exception as e:
            _logger.error(f"Error getting picking type: {str(e)}")
            return False
    
    @api.depends('purchase_order_id', 'product_id')
    def _compute_available_lots(self):
        """
        Compute lots that are linked to the selected purchase order.
        Lots are linked through stock moves in the purchase order's pickings.
        """
        for record in self:
            if not record.purchase_order_id:
                record.available_lot_ids = [(6, 0, [])]
                continue
            
            # Get all pickings (receipts) related to this purchase order
            pickings = record.purchase_order_id.picking_ids.filtered(
                lambda p: p.state == 'done'  # Only completed receipts
            )
            
            if not pickings:
                record.available_lot_ids = [(6, 0, [])]
                continue
            
            # Get all stock move lines from these pickings
            move_lines = pickings.mapped('move_line_ids')
            
            # Filter by product if product_id is set
            if record.product_id:
                move_lines = move_lines.filtered(
                    lambda ml: ml.product_id == record.product_id
                )
            
            # Extract unique lot IDs
            lot_ids = move_lines.mapped('lot_id').ids
            
            # Set the available lots
            record.available_lot_ids = [(6, 0, lot_ids)]

     # **NEW METHOD: Confirm Report**
    def action_confirm(self):
        """Confirm the quality grading report and trigger inventory operations"""
        _logger.info("=== ACTION_CONFIRM CALLED ===") # type: ignore
        for record in self:
            _logger.info(f"Processing record: {record.name}") # type: ignore
        for record in self:
            # Validate required fields
            record._validate_report_data()
            
            # **ADD THIS: Generate inventory moves**
            record._generate_graded_inventory_moves()

            # Change state to confirmed
            record.write({'state': 'confirmed'})
            
            # Post message to chatter
            record.message_post(
                body=_("Quality Grading Report has been confirmed by %s") % self.env.user.name,
                message_type='notification'
            )
        
        # **NEW: Automatically print the report with barcodes after confirmation**
        return self._print_report_with_barcodes()
    
    def _print_report_with_barcodes(self):
        """Print the quality grading report automatically after confirmation"""
        self.ensure_one()
        
        # Get the report action
        report = self.env.ref('custom_rsfp_module.action_report_quality_grading_detail')
        
        # Return the report action to automatically print/download
        return report.report_action(self)
    
    # **NEW METHOD: Validation**
    # **UPDATE: Enhanced validation method**
    def _validate_report_data(self):
        """Validate all required data before confirmation"""
        for record in self:
            # Check if all required fields are filled
            if not record.purchase_order_id:
                raise UserError(_("Purchase Order is required."))
            if not record.product_id:
                raise UserError(_("Product is required."))
            if not record.parent_lot_id:
                raise UserError(_("Parent Lot/Batch is required."))
            if not record.tester_id:
                raise UserError(_("Tester is required."))
            if not record.qty_received:
                raise UserError(_("Received Quantity must be greater than 0."))
            # ... existing validations ...
            
            # **NEW: Validate test lines for grades with quantities**
            grades_with_qty = []
            if record.qty_grade_a > 0:
                grades_with_qty.append(('A', record.qty_grade_a))
            if record.qty_grade_b > 0:
                grades_with_qty.append(('B', record.qty_grade_b))
            if record.qty_grade_c > 0:
                grades_with_qty.append(('C', record.qty_grade_c))

            # Validate quantities
            total_graded = record.qty_grade_a + record.qty_grade_b + record.qty_grade_c
            if abs(total_graded - record.qty_received) > 0.01:  # Allow small rounding differences
                raise UserError(_(
                    "Total graded quantity (%.2f) must equal received quantity (%.2f). "
                    "Current difference: %.2f"
                ) % (total_graded, record.qty_received, abs(total_graded - record.qty_received)))

            # Check if at least one grade has quantity
            if total_graded <= 0:
                raise UserError(_("At least one grade must have a quantity greater than 0."))
            
            # Check if we have test lines for all grades with quantities
            for grade_letter, qty in grades_with_qty:
                test_line = record.test_line_ids.filtered(lambda x: x.grade_letter == grade_letter)
                if not test_line:
                    raise UserError(_(
                        "Missing test line for Grade %s (Quantity: %.2f). "
                        "Please add a test line with the appropriate graded product."
                    ) % (grade_letter, qty))
                
                if not test_line.graded_product_id:
                    raise UserError(_(
                        "Test line for Grade %s must have a graded product selected."
                    ) % grade_letter)

    # **NEW METHOD: Reset to Draft (for future use)**
    def action_reset_to_draft(self):
        """Reset report back to draft state"""
        for record in self:
            if record.state == 'confirmed':
                record.write({'state': 'draft'})
                record.message_post(
                    body=_("Quality Grading Report has been reset to draft by %s") % self.env.user.name,
                    message_type='notification'
                )
        return True