{
    'name': 'Custom RSFP Module',
    'version': '1.0',
    'category': 'Quality/Purchase',
    'summary': 'Customized RSFP module for inventory management.',
    'depends': [
        'base',
        'purchase',
        'mail',
        'stock',
        'product',
        # 'barcodes',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/quality_sequence.xml',
        # Ensure this file name matches what is on your disk (view vs views)
        'views/quality_grading_views.xml', 
        # Rename 'views/report_action.xml' to the standard 'reports/...' path 
        # for better organization, or leave as is if it's already working.
        'views/report_action.xml', 
        
        # The commented out report template reference is CORRECTLY OMITTED from 'data'.

        'reports/custom_quality_report_templates.xml',
        'views/purchase_order_views.xml', 

        'views/product_template_views.xml',

        'data/lot_sequence_data.xml', 

        'views/stock_lot_views.xml',

        'data/stock_locations_data.xml',

        'views/sorting_report_views.xml',  # NEW: Add this line

        'views/quality_report_views.xml',  # NEW: Add this line

        'views/sorting_report_action.xml',  # NEW: Add this

        'views/quality_report_action.xml',  # NEW: Add this

        'reports/sorting_report_templates.xml',  # ← ADD THIS LINE

        'reports/quality_report_templates.xml',  # ← ADD THIS LINE
        



    ],
    'assets': {
        'web.assets_backend': [
            'custom_rsfp_module/static/src/js/stock_move_line.js',
        ],
    },
    
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
