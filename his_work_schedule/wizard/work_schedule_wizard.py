# -*- encoding:utf-8 -*-
from odoo import api, models, fields


class WorkScheduleWizard(models.TransientModel):
    _name = 'his.work_schedule_wizard'
    _description = '排班向导'

    start_date = fields.Date('开始日期')
    end_date = fields.Date('结束日期')

    department_id = fields.Many2one('hr.department', '科室')

    state = fields.Selection([('date', '选择日期')], '状态', default='date')





