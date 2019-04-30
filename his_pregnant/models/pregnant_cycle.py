# -*- encoding:utf-8 -*-
from odoo import api
from odoo import fields, models


class PregnantCycle(models.Model):
    _name = 'his.pregnant_cycle'
    _description = '孕周'
    update_external = True  # 更新外部服务器数据

    @api.model
    def _default_get_value(self):
        cycle = self.search([], order='value desc', limit=1)
        if cycle:
            return cycle.value + 1

        return 1

    name = fields.Char('名称')
    value = fields.Integer('距怀孕周数', default=_default_get_value)


    _sql_constraints = [
        ('value_uniq', 'unique (value)', '怀孕周数重复')
    ]

    @api.onchange('value')
    def onchange_value(self):
        if self.value < 1:
            return {
                'warning': {
                    'title': '距怀孕周数错误',
                    'message': "距怀孕周数必须大于等于1"
                }
            }

        self.name = u'第%d周' % self.value


