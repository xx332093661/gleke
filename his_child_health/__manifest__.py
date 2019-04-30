# -*- encoding:utf-8 -*-
{
    "name": "GLEKE儿童保健",
    "author": "liuchang",
    "depends": [
        'base',
        'product',
        'his_app_hcfy'
    ],
    "description": """""",
    
    'data': [
        'views/menu_view.xml',
        'views/child_health_inspection_item_view.xml',
        'views/child_health_inspection_view.xml',
        # # 'views/child_inspection_record_detail_view.xml',
        'views/child_inspection_record_view.xml',
        'views/child_view.xml',
        'views/child_health_register_view.xml',
        'views/child_health_schedule_view.xml',

        'data/child_health_cycle.xml',
    ],

    "installable": True,
    "application": True,
}
