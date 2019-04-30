# coding: utf-8

from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def _compute_age(self):
        for record in self:
            if record.birth_date:
                ages = self.compute_newborn_age(record.birth_date)  # 计算新生儿年龄
                record.age = '%d岁' % (ages.years + 1)

    @api.model
    def _default_get_birth_date(self):
        if self.env.context.get('patient_property') == 'newborn':
            return datetime.now().strftime(DATE_FORMAT)

    outpatient_num = fields.Char('门诊号')
    card_no = fields.Char('就诊卡号')
    session_id = fields.Char('sessionId')
    gender = fields.Selection([('male', '男'), ('female', '女')], '性别')
    birth_date = fields.Date('出生日期', default=_default_get_birth_date)
    age = fields.Char('年龄', help='患者性质不为新生儿, 用此字段表示年龄', compute='_compute_age')

    topic = fields.Char('主题')

    @staticmethod
    def compute_newborn_age(birthday):
        """计算新生儿年龄"""
        today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)  # 当前日期
        birthday = datetime.strptime(birthday, DATE_FORMAT)  # 出生日期
        ages = relativedelta(today, birthday)  # 新生儿年龄
        return ages
