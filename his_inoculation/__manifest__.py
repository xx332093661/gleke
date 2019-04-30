# -*- encoding:utf-8 -*-
{
    "name": "GLEKE预防接种",
    'category': 'app',
    'version': '1.0',
    "depends": [
        'base', 'sale', 'his_app_hcfy'
    ],
    "description": """""",
    
    'data': [
        'data/inoculation_cycle.xml',
        'data/inoculation_item.xml',
        'data/inoculation_schedule.xml',
        'data/inoculation_schedule_detail.xml',

        'views/menu_view.xml',
        #
        'views/inoculation_item_view.xml',
        'views/inoculation_schedule_view.xml',
        'views/inoculation_record_view.xml',
        'views/newborn_manage_view.xml',
        'views/inoculation_personal_schedule_view.xml',
        'views/inoculation_register_view.xml',
        'views/inoculation_cycle_view.xml',
        #
        # 'views/partner_view.xml',
    ],

    "installable": True,
    "application": True,
}
