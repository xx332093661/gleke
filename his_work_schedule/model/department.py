# -*- encoding:utf-8 -*-
from odoo import api
from odoo import models, fields


class Department(models.Model):
    _inherit = 'hr.department'

    is_shift = fields.Boolean('参与排班')
    is_outpatient = fields.Boolean('是门诊科室')
    max_execute_count = fields.Integer('最大执行数量')
    category_id = fields.Many2one('hrp.department_category', '科室分类')
    employees = fields.One2many('his.schedule_department_employee', 'department_id', string='人员')
    shift_type_ids = fields.One2many('his.shift_type', 'department_id', string='班次')


    @api.multi
    def set_default_shift_type(self):
        shift_type_obj = self.env['his.shift_type']
        self.shift_type_ids.unlink()
        for shift in self.env['his.shift_type_default'].search([]):
            shift_type_obj.create({
                'department_id': self.id,
                'name': shift.name,
                'start_time': shift.start_time,
                'end_time': shift.end_time,
                'color': shift.color,
                'label': shift.label,
                'type': shift.type
            })
        return {}


    # @api.onchange('is_shift')
    # def is_shift_changed(self):
    #     self.is_outpatient = self.is_shift



