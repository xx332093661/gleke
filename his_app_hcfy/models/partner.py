# -*- encoding:utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re

from odoo import api
from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.exceptions import Warning


class Partner(models.Model):
    _inherit = 'res.partner'


    @api.model
    def _default_get_patient_property(self):
        if self.env.context.get('patient_property'):
            return self.env.context.get('patient_property')

    @api.model
    def _default_get_is_patient(self):
        if self.env.context.get('patient_property') in ['newborn', 'pregnant', 'normal']:
            return True

    @api.model
    def _default_get_birth_date(self):
        if self.env.context.get('patient_property') == 'newborn':
            return datetime.now().strftime(DATE_FORMAT)


    is_patient = fields.Boolean('患者', default=_default_get_is_patient)
    is_doctor = fields.Boolean('医生')
    gender = fields.Selection([('male', '男'), ('female', '女')], '性别')
    birth_date = fields.Date('出生日期', default=_default_get_birth_date)
    month_label = fields.Char('年龄', compute='_compute_month_label', help='患者性质是新生儿, 用此字段表示年龄')
    age = fields.Char('年龄', help='患者性质不为新生儿, 用此字段表示年龄', compute='_compute_age')

    patient_property = fields.Selection([('pregnant', '孕妇'), ('newborn', '新生儿'), ('normal', '正常')], '患者性质', default=_default_get_patient_property)
    work_company = fields.Char('工作单位')
    address = fields.Char('家庭住址')
    extranet_id = fields.Integer('外部ID')
    card_type_id = fields.Char('卡类别ID')
    topic = fields.Char('主题')

    @staticmethod
    def compute_newborn_age(birthday):
        """计算新生儿年龄"""
        today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)  # 当前日期
        birthday = datetime.strptime(birthday, DATE_FORMAT)  # 出生日期
        ages = relativedelta(today, birthday)  # 新生儿年龄
        return ages

    @api.multi
    def _compute_age(self):
        for record in self:
            if record.birth_date:
                ages = self.compute_newborn_age(record.birth_date)  # 计算新生儿年龄
                record.age = '%d岁' % (ages.years + 1)


    @api.onchange('birth_date')
    def onchange_birth_date(self):

        if self.birth_date:
            today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)
            birth_date = datetime.strptime(self.birth_date, DATE_FORMAT)
            if birth_date > today:
                raise Warning('出生日期不能大于当天日期')

        if self.env.context.get('patient_property') == 'newborn':
            if self.birth_date:
                ages = self.compute_newborn_age(self.birth_date)  # 计算新生儿年龄
                months = ages.years * 12 + ages.months  # 出生到现在月数
                if not months:
                    self.month_label = '%d天' % ages.days
                elif not ages.years:
                    self.month_label = '%d个月+%d天' % (ages.months, ages.days) if ages.days else '%d个月' % ages.months
                else:
                    if ages.years >= 7:
                        self.month_label = '%d周岁' % ages.years
                    else:
                        if not ages.months:
                            self.month_label = '%d周岁' % ages.years
                        elif ages.months == 6:
                            self.month_label = '%d岁半' % ages.years
                        else:
                            self.month_label = '%d岁%d个月' % (ages.years, ages.months)

        if self.env.context.get('patient_property') == 'pregnant':
            if self.birth_date:
                ages = self.compute_newborn_age(self.birth_date)  # 计算新生儿年龄
                self.age = u'%d岁' % (ages.years + 1)
            else:
                self.age = False


    @api.onchange('id_no')
    def onchange_id_no(self):
        if self.env.context.get('patient_property') == 'pregnant':
            if self.id_no:
                if not self.check_identity(self.id_no): # 验证身份证
                    raise Warning('身份证号错误!')
                else:
                    self.birth_date = '%s-%s-%s' % (self.id_no[6:10], self.id_no[10:12], self.id_no[12:14])
            else:
                self.birth_date = False


    @api.multi
    def _compute_month_label(self):
        for record in self:
            if not record.birth_date:
                continue

            ages = self.compute_newborn_age(record.birth_date)  # 计算新生儿年龄
            months = ages.years * 12 + ages.months  # 出生到现在月数
            if not months:
                record.month_label = '%d天' % ages.days
            elif not ages.years:
                record.month_label = '%d个月+%d天' % (ages.months, ages.days) if ages.days else '%d个月' % ages.months
            else:
                if ages.years >= 7:
                    record.month_label = '%d周岁' % ages.years
                else:
                    if not ages.months:
                        record.month_label = '%d周岁' % ages.years
                    elif ages.months == 6:
                        record.month_label = '%d岁半' % ages.years
                    else:
                        record.month_label = '%d岁%d个月' % (ages.years, ages.months)


    @staticmethod
    def check_identity(id_no):
        """验证身份证"""
        # identity_pattern_str = config['identity_pattern_str']

        identity_pattern = re.compile('^[1-9]\d{5}[1-9]\d{3}((0\d)|(1[0-2]))(([0|1|2]\d)|3[0-1])\d{3}([0-9]|X)$')
        id_group = identity_pattern.match(id_no)
        if not id_group:
            return False
        return True






