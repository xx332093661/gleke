# -*- coding: utf-8 -*-
from odoo import models, fields, api


class InoculationCycle(models.Model):
    _name = 'his.inoculation_cycle'
    _description = '接种周期'
    update_external = True  # 更新外部服务器数据

    name = fields.Char('名称', required=True)
    value = fields.Integer('出生月数')

    _sql_constraints = [
        ('value_uniq', 'unique (value)', '出生月数重复')
    ]

    @api.onchange('value')
    def onchange_value(self):
        """计算value"""
        if self.value < 0:
            return {
                'warning': {
                    'title': '出生月数错误',
                    'message': "出生月数必须大于等于0"
                }
            }

        years, months = divmod(self.value, 12)
        if not years:
            self.name = u'%s月龄' % self.value
        else:
            if not months:
                self.name = u'%d周岁' % years
            else:
                if months == 6:
                    self.name = u'%d岁半' % years
                else:
                    self.name = u'%d岁%d个月' % (years, months)





