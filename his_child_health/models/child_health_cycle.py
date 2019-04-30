# -*- encoding:utf-8 -*-
from odoo import fields, models


class ChildHealthCycle(models.Model):
    _name = 'his.child_health_cycle'
    _description = '儿保周期'
    update_external = True  # 更新外部服务器数据


    month = fields.Integer('月龄')






