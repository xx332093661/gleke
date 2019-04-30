# -*- encoding:utf-8 -*-
from odoo import models, fields




class Employee(models.Model):
    _inherit = 'hr.employee'

    # work_schedule_group_id = fields.Many2one('his.employee_group', '组')
    # title = fields.Char('专业技术职务')
    # work_schedule_department_id = fields.Many2one('hr.department', '科室')
    # register_time_interval = fields.Char('挂号时间间隔')


