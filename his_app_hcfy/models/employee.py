# -*- encoding:utf-8 -*-
from odoo import models, fields


class Employee(models.Model):
    _inherit = 'hr.employee'
    update_external = True  # 更新外部服务器数据

    good_at = fields.Text('擅长')
    title = fields.Char('技术职务')
    introduction = fields.Text('简介')

