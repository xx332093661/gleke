# -*- encoding:utf-8 -*-
{
    "name": "排队管理",
    "author": "liuchang",
    "depends": [
        'base',
        'hr',
        'product',
    ],
    "description": """""",
    
    'data': [
        # 'wizard/hrp_schedule_wizard_view.xml',
        'views/menu_view.xml',

        'views/hrp_queue_view.xml',
        'views/hrp_hr_view.xml',
        'views/hrp_equipment_view.xml',
        'views/hrp_queue_set_view.xml',
        'views/hrp_res_view.xml',
        # 'views/hrp_schedule_view.xml',

        'views/hrp_treatment_process_view.xml',

        # 'views/inoculation_item_view.xml',
        # 'views/inoculation_schedule_view.xml',
        # 'views/inoculation_record_view.xml',

        'views/hrp_templates.xml',

        'hrp_queue_data.xml',

        'security/ir.model.access.csv',
        'security/hrp_security.xml',

        'report/hrp_queue_report_view.xml',


        'views/web_asset_backend_template.xml',
    ],
    # 'qweb': [
    #     "static/src/xml/work_schedule.xml",
    # ],
    "installable": True,
    "application": True,
}
