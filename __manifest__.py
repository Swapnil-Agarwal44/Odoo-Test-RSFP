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
        'barcodes',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',

        'data/quality_sequence.xml',

        'views/quality_menu.xml',

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
        
        'reports/lot_label_templates.xml',

        'views/child_lot_creation_views.xml',

        'reports/child_lot_creation_templates.xml',


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
