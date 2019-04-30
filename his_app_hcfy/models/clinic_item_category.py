# -*- encoding:utf-8 -*-
from odoo import api
from odoo import models, fields


class ClinicItemCategory(models.Model):
    _inherit = 'his.clinic_item_category'
    _description = '诊疗项目目录'


    is_shift = fields.Boolean('参与排班')
    department_id = fields.Many2one('hr.department', '执行科室')
    max_days = fields.Integer('最大排班时长', help='单位：天')

    @api.multi
    def write(self, vals):
        if 'is_shift' in vals:
            if not vals['is_shift']:
                department = self.department_id
                if department:
                    department.shift_type_ids.unlink()
                    department.employees.unlink()
                    department.write({
                        'is_shift': False,
                        'is_outpatient': False,
                    })
                    vals.update({
                        'department_id': False,
                        'max_days': False
                    })
            else:
                self.env['hr.department'].browse(vals['department_id']).write({
                    'is_shift': True,
                    'is_outpatient': False,
                })

        return super(ClinicItemCategory, self).write(vals)
