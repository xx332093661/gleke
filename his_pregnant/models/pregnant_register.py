# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import Warning



class PregnantRegister(models.Model):
    _name = 'his.pregnant_register'
    _description = u'产检登记'
    _order = 'id desc'
    update_external = True  # 更新外部服务器数据

    name = fields.Char('孕妇姓名')
    pregnant_identity_no = fields.Char('身份证号')
    last_menstruation_day = fields.Date('末次月经日期')
    plan_born_day = fields.Date('预产期')
    address = fields.Char('现住址')
    permanent_address = fields.Char('户籍地址')
    phone = fields.Char('联系电话')
    document_no = fields.Char('档案号')
    community = fields.Char('居委会')
    register_date = fields.Date('登记日期', default=lambda x: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT))
    pregnant_count = fields.Selection([(str(i), '第%d次怀孕' % i) for i in range(1, 20, 1)], '孕次', default='1')
    childbirth_count = fields.Selection([(str(i), '%d胎' % i) for i in range(0, 20, 1)], '产次(产过几胎)', default='0')
    person_liable = fields.Char('产检责任人')
    age = fields.Char('年龄', compute='_compute_age')
    birth_date = fields.Date('出生日期')


    _sql_constraints = [
        ('value_uniq', 'check (pregnant_count>=childbirth_count)', '产次不能大于孕次')
    ]


    @api.onchange('pregnant_count', 'childbirth_count')
    def onchange_pregnant_count(self):
        if self.pregnant_count and self.childbirth_count:
            if int(self.childbirth_count) > int(self.pregnant_count):
                return {
                    'warning': {
                        'title': '孕产次错误',
                        'message': "产次不能大于孕次1"
                    }
                }


    @api.onchange('birth_date')
    def onchange_birth_date(self):
        if self.birth_date:
            ages = self.env['res.partner'].compute_newborn_age(self.birth_date)  # 计算新生儿年龄
            self.age = u'%d岁' % (ages.years + 1)
        else:
            self.age = ''

    @api.onchange('pregnant_identity_no')
    def onchange_pregnant_identity_no(self):
        if self.pregnant_identity_no:
            if not self.env['res.partner'].check_identity(self.pregnant_identity_no): # 验证身份证
                raise Warning('身份证号错误!')
            else:
                self.birth_date = '%s-%s-%s' % (self.pregnant_identity_no[6:10], self.pregnant_identity_no[10:12], self.pregnant_identity_no[12:14])
                pregnant_register = self.search([('pregnant_identity_no', '=', self.pregnant_identity_no)], order='id desc', limit=1)
                if pregnant_register:
                    self.pregnant_count = str(int(pregnant_register.pregnant_count) + 1)
                    self.childbirth_count = str(int(pregnant_register.childbirth_count) + 1)
                    self.name = pregnant_register.name
        else:
            self.birth_date = False
            self.pregnant_count = '1'
            self.childbirth_count = '0'

    @api.multi
    def _compute_age(self):
        for record in self:
            if record.birth_date:
                ages = self.env['res.partner'].compute_newborn_age(record.birth_date)  # 计算新生儿年龄
                record.age = u'%d岁' % (ages.years + 1)


    @api.model
    def create(self, vals):
        pregnant_identity_no = vals['pregnant_identity_no'] # 身份证号
        if pregnant_identity_no:
            if not self.env['res.partner'].check_identity(pregnant_identity_no):  # 验证身份证
                raise Warning('身份证号错误!')

            vals['birth_date'] = '%s-%s-%s' % (pregnant_identity_no[6:10], pregnant_identity_no[10:12], pregnant_identity_no[12:14])
        return super(PregnantRegister, self).create(vals)


    @api.multi
    def write(self, vals):
        if 'pregnant_identity_no' in vals:
            if not self.env['res.partner'].check_identity(vals['pregnant_identity_no']):  # 验证身份证
                raise Warning('身份证号错误!')

        return super(PregnantRegister, self).write(vals)



