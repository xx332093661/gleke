# -*- encoding:utf-8 -*-
{
    "name": "GLEKE",
    "author": "liuchang",
    "depends": ['base', 'sale', 'his_work_schedule'],
    "description": """""",
    
    'data': [
        'views/menu_view.xml',
        'views/employee_view.xml',
        'views/department_view.xml',
        'views/company_view.xml',
        'views/partner_view.xml',
        'views/identity_view.xml',
        'views/medical_insurance_view.xml',

        'views/base_data_message_view.xml',
        'views/app_function_view.xml',
        'views/weixin_pay_view.xml',
        'views/alipay_view.xml',
        'views/long_pay_record_view.xml',
        # 'views/appointment_record_view.xml',
        'views/product_view.xml',
        'views/reserve_record_view.xml',
        'views/order_view.xml',
        'views/refund_apply_view.xml',
        'views/post_bar_view.xml',

        'views/templates.xml',

        'data/ir_cron.xml',
        'data/sequence.xml',
        'security/ir.model.access.csv',
    ],

    "installable": True,
    "application": True,
}
