# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class ChildHealthRegister(models.Model):
    _name = 'his.child_health_register'
    _description = '儿保登记'
    _order = 'id desc'
    update_external = True  # 更新外部服务器数据

    document_no = fields.Char('档案号')
    name = fields.Char('姓名')
    gender = fields.Selection([('male', '男'), ('female', '女'), ('unknown', '未知')], '性别')
    age = fields.Char('年龄', compute='_compute_age')
    birth_date = fields.Date('出生日期')
    address = fields.Char('现住址')
    father_name = fields.Char('父亲姓名')
    father_identity_no = fields.Char('父亲身份证')
    mother_name = fields.Char('母亲姓名')
    mother_identity_no = fields.Char('母亲身份证')
    community = fields.Char('居委会')
    phone = fields.Char('联系电话')
    person_liable = fields.Char('责任人')
    register_date = fields.Date('登记日期', default=lambda x: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT))
    permanent_address = fields.Char('户籍地址')


    @api.onchange('birth_date')
    def onchange_birth_date(self):
        if self.birth_date:
            ages = self.env['res.partner'].compute_newborn_age(self.birth_date)
            months = ages.years * 12 + ages.months  # 出生到现在月数
            if not months:
                self.age = '%d天' % ages.days
            elif not ages.years:
                self.age = '%d个月+%d天' % (ages.months, ages.days) if ages.days else '%d个月' % ages.months
            else:
                if ages.years >= 7:
                    self.age = '%d周岁' % ages.years
                else:
                    if not ages.months:
                        self.age = '%d周岁' % ages.years
                    elif ages.months == 6:
                        self.age = '%d岁半' % ages.years
                    else:
                        self.age = '%d岁%d个月' % (ages.years, ages.months)

        else:
            self.age = False

    @api.multi
    def _compute_age(self):
        for record in self:
            if not record.birth_date:
                continue

            ages = self.env['res.partner'].compute_newborn_age(record.birth_date)  # 计算新生儿年龄
            months = ages.years * 12 + ages.months  # 出生到现在月数
            if not months:
                record.age = '%d天' % ages.days
            elif not ages.years:
                record.age = '%d个月+%d天' % (ages.months, ages.days) if ages.days else '%d个月' % ages.months
            else:
                if ages.years >= 7:
                    record.age = '%d周岁' % ages.years
                else:
                    if not ages.months:
                        record.age = '%d周岁' % ages.years
                    elif ages.months == 6:
                        record.age = '%d岁半' % ages.years
                    else:
                        record.age = '%d岁%d个月' % (ages.years, ages.months)