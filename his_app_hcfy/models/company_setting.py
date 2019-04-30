# -*- encoding:utf-8 -*-
from odoo import api
from odoo import fields, models



class Configuration(models.TransientModel):
    _name = 'his.company_settings'
    _inherit = 'res.config.settings'
    _description = '医院信息设置'

    name = fields.Char('医院名称')
    topic = fields.Char('订阅主题')
    longitude = fields.Char('经度')
    latitude = fields.Char('纬度')
    range = fields.Integer('定位精度(米)')
    appoint_day = fields.Integer('预约挂号天数')

    his_user_id = fields.Char('HIS用户ID')
    inoculation_department_id = fields.Many2one('hr.department', '预防接种科室')
    inoculation_appoint_day = fields.Integer('预防接种预约天数')
    pregnant_department_id = fields.Many2one('hr.department', '产检预约科室')
    child_health_department_id = fields.Many2one('hr.department', '儿保预约科室')

    @api.multi
    def get_default_name(self, _):
        return {'name': self.env.user.company_id.name}

    @api.multi
    def get_default_topic(self, _):
        return {'topic': self.env.user.company_id.topic}

    @api.multi
    def get_default_longitude(self, _):
        return {'longitude': self.env.user.company_id.longitude}

    @api.multi
    def get_default_latitude(self, _):
        return {'latitude': self.env.user.company_id.latitude}

    @api.multi
    def get_default_range(self, _):
        return {'range': self.env.user.company_id.range}

    @api.multi
    def get_default_appoint_day(self, _):
        return {'appoint_day': self.env.user.company_id.appoint_day}


    @api.multi
    def get_default_his_user_id(self, _):
        return {'his_user_id': self.env.user.company_id.his_user_id}

    @api.multi
    def get_default_inoculation_department_id(self, _):
        return {'inoculation_department_id': self.env.user.company_id.inoculation_department_id.id}

    @api.multi
    def get_default_pregnant_department_id(self, _):
        return {'pregnant_department_id': self.env.user.company_id.pregnant_department_id.id}

    @api.multi
    def get_default_child_health_department_id(self, _):
        return {'child_health_department_id': self.env.user.company_id.child_health_department_id.id}

    @api.multi
    def get_default_inoculation_appoint_day(self, _):
        return {'inoculation_appoint_day': self.env.user.company_id.inoculation_appoint_day}


    @api.multi
    def set_default_appoint_day(self):
        cols = ['name', 'topic', 'longitude', 'latitude', 'range', 'appoint_day', 'his_user_id', 'inoculation_appoint_day']

        vals = {}
        for key in cols:
            if getattr(self, key) != getattr(self.env.user.company_id, key):
                vals[key] = getattr(self, key)

        inoculation_department_id = self.inoculation_department_id.id
        if inoculation_department_id != self.env.user.company_id.inoculation_department_id.id:
            vals['inoculation_department_id'] = inoculation_department_id

        pregnant_department_id = self.pregnant_department_id.id
        if pregnant_department_id != self.env.user.company_id.pregnant_department_id.id:
            vals['pregnant_department_id'] = pregnant_department_id

        child_health_department_id = self.child_health_department_id.id
        if child_health_department_id != self.env.user.company_id.child_health_department_id.id:
            vals['child_health_department_id'] = child_health_department_id


        if vals:
            self.env.user.company_id.write(vals)

        return True






