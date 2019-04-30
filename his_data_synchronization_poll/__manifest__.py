# -*- coding: utf-8 -*-

{
    'name': 'His Data Synchronization Poll',
    'category': 'his',
    'version': '1.0',
    'description': '',
    'depends': ['base', 'hr', 'hrp_queue'],
    'data': [
        'data/subscribe_type.xml',

        'views/menuitem.xml',

        'views/sync_define_view.xml',
        #
        # 'views/menuitem.xml',
        'views/notify_data_view.xml',
        'views/notify_data_history_view.xml',
        # # 'views/query_data_view.xml',
        # 'views/notify_data_all_view.xml',
        'views/poll_data_view.xml',
        'views/poll_data_history_view.xml',
        #
        'views/total_queue_view.xml',
        #
        # 'views/department_view.xml',
        # 'views/employee_view.xml',
        #
        # 'wizard/retrieve_miss_notify_view.xml',
        #
        #
        'data/ir_cron.xml',

    ],
    'demo': [

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],

    'bootstrap': False,  # load translations for login screen
}
