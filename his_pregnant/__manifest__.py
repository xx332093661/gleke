# -*- encoding:utf-8 -*-
{
    "name": "GLEKE孕产管理",
    "author": "liuchang",
    "depends": [
        'base',
        'sale',
        'his_app_hcfy'
    ],
    "description": """""",
    
    'data': [
        'data/pregnant_cycle.xml',
        'data/pregnant_inspection_item.xml',
        'data/pregnant_inspection.xml',

        'views/menu_view.xml',
        'views/pregnant_cycle_view.xml',
        'views/pregnant_register_view.xml',
        # 'views/baby_grow_image_view.xml',
        # 'views/mother_grow_view.xml',
        'views/pregnant_inspection_item_view.xml',
        'views/pregnant_inspection_view.xml',
        'views/mother_inspection_detail_view.xml',
        'views/mother_inspection_view.xml',
        'views/pregnant_woman_view.xml',
        'views/pregnant_schedule_view.xml',

    ],

    "installable": True,
    "application": True,
}
