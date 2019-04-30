# -*- coding: utf-8 -*-

{
    'name': 'His Data Sync HCFY',
    'category': 'his',
    'version': '1.0',
    'description': '',
    'depends': ['base', 'his_data_synchronization_poll', 'sale'],
    'data': [
        'data/sync_define.xml',
        #
        'views/clinic_classification_category_view.xml',
        'views/clinic_item_category_view.xml',
        'views/clinic_item_part_view.xml',
        'views/register_view.xml',
        'views/dispose_view.xml',
        'views/dispose_send_view.xml',
        'views/outpatient_fee_view.xml',
        'views/hrp_business_view.xml',
        'views/department_view.xml',
        'views/employee_view.xml',

    ],
    'demo': [

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],

    'bootstrap': False,  # load translations for login screen
}
