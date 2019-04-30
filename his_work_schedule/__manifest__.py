# -*- coding: utf-8 -*-

{
    'name': 'GLEKE科室排班',
    'category': 'his',
    'version': '1.0',
    'description': '',
    'depends': ['hr', 'web', 'web_widget_color', 'product'],
    'data': [
        'views/web_asset_backend_template.xml',
        'views/menu.xml',
        'views/shift_type_view.xml',
        'views/work_schedule_view.xml',
        'views/shift_type_default_view.xml',
        'views/department_category_view.xml',
        'views/department_view.xml',

        'views/schedule_shift_view.xml',
        'views/register_source_view.xml',


    ],
    'demo': [

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [
        "static/src/xml/*.xml",
    ],

    'bootstrap': False,  # load translations for login screen
}
