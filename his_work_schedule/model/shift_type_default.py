# -*- encoding:utf-8 -*-
from odoo import models, fields, api


class ShiftTypeDefault(models.Model):
    _name = 'his.shift_type_default'
    _description = '全局班次'
    update_external = True  # 更新外部服务器数据


    name = fields.Char('名称', required=True)
    start_time = fields.Float('上班时间', required=True)
    end_time = fields.Float('下班班时间', required=True)
    color = fields.Char('颜色', default='#eeeeee')
    label = fields.Char('显示')
    type = fields.Selection([('1', '工作'), ('2', '非工作')], '班次类型', default='1')

    @api.onchange('name')
    def onchange_name(self):
        if self.name:
            self.label = self.name[0]


    @api.multi
    def write(self, vals):
        result = super(ShiftTypeDefault, self).write(vals)

        if 'color' in vals:
            for shift_type in self.env['his.shift_type'].search([('name', '=', self.name)]):
                shift_type.write({'color': vals['color']})

        return result






