# -*- encoding:utf-8 -*-
from odoo import models, fields


class DepartmentCategory(models.Model):
    _name = 'hrp.department_category'
    _description = '科室分类'
    update_external = True  # 更新外部服务器数据

    name = fields.Char('名称', required=True)




