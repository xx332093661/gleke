# -*- encoding:utf-8 -*-
from odoo import fields, models


class PayMethod(models.Model):
    _name = 'his.pay_method'
    _description = '支付方式与中联卡类别对应'

    name = fields.Char('名称', required=1)
    pay_method = fields.Char('支付方式', required=1)
    his_card_type_id = fields.Char('中联卡类别ID', required=1)
