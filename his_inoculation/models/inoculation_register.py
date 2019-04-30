# -*- encoding:utf-8 -*-
from datetime import datetime

from odoo import fields, models, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class InoculationRegister(models.Model):
    _name = 'his.inoculation_register'
    _description = '接种登记'
    update_external = True  # 更新外部服务器数据


    name = fields.Char('儿童姓名')

    code = fields.Char('儿童编码')
    note_code = fields.Char('接种本条形码')

    inoculation_identity_no = fields.Char('监护人身份证号')
    birth_code = fields.Char('出生证号')
    gender = fields.Selection([('male', '男'), ('female', '女')], '性别')
    birth_date = fields.Date('出生日期')
    birth_hospital = fields.Char('出生医院', default=lambda self: self.env.user.company_id.name)
    birth_weight = fields.Char('出生体重(kg)')
    guardian = fields.Char('监护人')
    guardian_relationship = fields.Char('与儿童关系')
    address = fields.Char('家庭住址')
    permanent_address = fields.Char('户籍地址')
    allergic_history = fields.Char('过敏史')
    inoculation_taboo = fields.Char('接种禁忌')
    phone = fields.Char('接种单位电话', default=lambda self: self.env.user.company_id.phone)

    register_date = fields.Date('登记日期', default=lambda self: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT))


    @api.onchange('birth_weight')
    def onchange_birth_weight(self):
        if self.birth_weight:
            birth_weight = self.birth_weight.replace(u'千克', u'').replace(u'公斤', u'').replace(u'kg', u'').replace(u'KG', u'')
            if birth_weight.endswith(u'g') or birth_weight.endswith(u'G'):
                birth_weight = birth_weight.replace(u'g', '').replace(u'G', '')
                try:
                    birth_weight = round(int(birth_weight) / 1000.0, 1)
                    self.birth_weight = '%skg' % birth_weight
                except ValueError:
                    self.birth_weight = ''
            elif birth_weight.endswith(u'斤'):
                birth_weight = birth_weight.replace(u'斤', '')
                try:
                    birth_weight = float(birth_weight)
                    self.birth_weight = '%skg' % round(birth_weight / 2, 1)
                except ValueError:
                    self.birth_weight = ''
            else:
                try:
                    birth_weight = float(birth_weight)
                    self.birth_weight = '%skg' % birth_weight
                except ValueError:
                    self.birth_weight = ''






