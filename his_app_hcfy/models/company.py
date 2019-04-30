# -*- encoding:utf-8 -*-
from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'
    update_external = True  # 更新外部服务器数据

    topic = fields.Char('订阅主题')
    longitude = fields.Char('经度')
    latitude = fields.Char('纬度')
    range = fields.Integer('定位精度')
    appoint_day = fields.Integer('预约挂号天数')
    his_user_id = fields.Char('HIS用户ID')
    inoculation_department_id = fields.Many2one('hr.department', '预防接种科室')
    inoculation_appoint_day = fields.Integer('预防接种预约天数')
    pregnant_department_id = fields.Many2one('hr.department', '产检预约科室')
    child_health_department_id = fields.Many2one('hr.department', '儿保预约科室')






