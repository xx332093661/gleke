# -*- coding: utf-8 -*-

{
    'name': 'GLEKE',
    'category': 'app',
    'version': '1.0',
    'description': '',
    'depends': ['base', 'his_work_schedule', 'sale', 'his_data_sync_hcfy'],
    'data': [
        'views/menu.xml',
        'views/employee_view.xml',
        'views/product_view.xml',
        'views/base_data_message_view.xml',
        'views/register_plan_view.xml',
        'views/weixin_pay_view.xml',
        'views/alipay_view.xml',
        'views/order_view.xml',
        'views/reserve_record_view.xml',
        'views/company_view.xml',
        'views/company_setting_view.xml',
        'views/register_view.xml',

        'views/clinic_item_category_view.xml',
        'views/pay_method_view.xml',

        'views/partner_view.xml',
        'views/refund_apply_view.xml',
        'views/long_pay_record_view.xml',

        'data/ir_cron.xml',
        'data/partner_sequence.xml',
        'data/product_category.xml',

    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
    'bootstrap': False,  # load translations for login screen
}
