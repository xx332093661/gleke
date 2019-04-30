# -*- encoding:utf-8 -*-
{
    "name": "GLEKE便民服务",
    "author": "liuchang",
    "depends": [
        'base',
        'product',
        'his_app_hcfy'
    ],
    "description": """""",
    
    'data': [

        'views/menu_view.xml',
        'views/convenient_service_category_view.xml',
        'views/convenient_item_service_view.xml',
        'views/convenient_item_medicine_view.xml',
        'views/convenient_item_inspection_view.xml',
        'views/convenient_item_checkout_view.xml',
        'views/convenient_item_physical_view.xml',

        #
        # 'wizard/drug_manual_wizard_view.xml',
        #
        'data/convenient_service_category.xml',
    ],

    "installable": True,
    "application": True,
}
