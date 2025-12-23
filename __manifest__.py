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
        # Security
        'security/ir.model.access.csv',

        # Data (Sequences, Locations, Warehouses)
        'data/quality_sequence.xml',
        'data/lot_sequence_data.xml',
        'data/stock_locations_data.xml',
        'data/warehouse_data.xml',

        # Menus
        'views/quality_menu.xml',

        # Views
        'views/purchase_order_views.xml',
        'views/product_template_views.xml',
        'views/stock_lot_views.xml',
        'views/sorting_report_views.xml',
        'views/quality_report_views.xml',
        'views/sorting_report_action.xml',
        'views/quality_report_action.xml',
        'views/child_lot_creation_views.xml',
        'views/lot_label_wizard_views.xml',
        'views/custom_lot_label_button.xml',

        # Reports
        'reports/custom_quality_report_templates.xml',
        'reports/sorting_report_templates.xml',
        'reports/quality_report_templates.xml',
        'reports/lot_label_templates.xml',
        'reports/child_lot_creation_templates.xml',
        'reports/report_override.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_rsfp_module/static/src/js/stock_move_line.js',
            'custom_rsfp_module/static/src/js/zpl_printer.js',
        ],
    },
    
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
