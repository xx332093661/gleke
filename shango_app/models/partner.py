# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import Warning
from odoo.tools import config
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

import threading
import random
import logging
import string
import re

partner_code_lock = threading.Lock()
partner_code_sequence = []
_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _generate_partner_code(self):
        """生成GLEKE码"""
        def get_code():
            code = self.env['ir.sequence'].next_by_code('res.partner.code')
            if code and self.search([('code', '=', code)]):
                return get_code()
            return code

        return get_code()

    @api.multi
    def _compute_relation(self):
        partner_relationship_obj = self.env['his.partner_relationship']
        for partner in self:
            partner_relationship = partner_relationship_obj.search([('partner_id', '=', partner.id)], limit=1)
            if not partner_relationship:
                continue
            partner.relation_partner_id = partner_relationship.parent_id.id
            partner.relationship = partner_relationship.relationship

    @api.model
    def _default_get_patient_property(self):
        if self.env.context.get('patient_property'):
            return self.env.context.get('patient_property')


    @api.model
    def _default_get_is_patient(self):
        if self.env.context.get('patient_property') in ['newborn', 'pregnant', 'normal']:
            return True


    @api.model
    def _default_get_gender(self):
        if self.env.context.get('patient_property') == 'pregnant':
            return 'female'

    code = fields.Char('GLEKE码', default=_generate_partner_code, select=1)
    relationship_ids = fields.One2many('his.partner_relationship', 'parent_id', '联系人')
    is_patient = fields.Boolean('患者', default=_default_get_is_patient)
    is_doctor = fields.Boolean('医生')
    birth_date = fields.Date('出生日期')
    age = fields.Char('年龄', compute='_compute_age')
    month_label = fields.Char('年龄', compute='_compute_month_label', help='患者性质是新生儿, 用此字段表示年龄')

    relation_partner_id = fields.Many2one('res.partner', '关系人', compute=_compute_relation)
    relationship = fields.Selection([('self', '本人'), ('child', '子女'), ('parents', '父母'), ('husband-wife', '夫妻'), ('friend', '朋友'), ('other', '其他')], '关系', compute=_compute_relation)

    patient_property = fields.Selection([('normal', '普通'), ('newborn', '新生儿'), ('pregnant', '孕妇')], '患者性质', default=_default_get_patient_property)
    gender = fields.Selection([('male', '男'), ('female', '女')], '性别', default=_default_get_gender)
    identity_no = fields.Char('身份证号')
    medical_card = fields.Char('医保卡号')
    address = fields.Char('住址')
    work_company = fields.Char('工作单位')
    patient_ids = fields.One2many('hrp.patient', 'partner_id', '患者')
    employee_ids = fields.Many2many('hr.employee', 'app_partner_employee_rel', 'partner_id', 'employee_id', '员工')

    password = fields.Char('密码')
    work = fields.Char('职业')

    qq = fields.Char('QQ号')
    wx = fields.Char('微信号')
    identity_id = fields.Many2one('hrp.identity', '身份证')
    medical_insurance_id = fields.Many2one('hrp.medical_insurance', '医保卡')

    # 身份证信息
    i_identity_num = fields.Char('身份证号', related='identity_id.identity_num')
    i_name = fields.Char('姓名', related='identity_id.name')
    i_gender = fields.Char('性别', related='identity_id.gender')
    i_nation = fields.Char('民族', related='identity_id.nation')
    i_birth_date = fields.Date('出生日期', related='identity_id.birth_date')
    i_address = fields.Char('住址', related='identity_id.address')

    # 医保卡信息
    mi_num = fields.Char(related='medical_insurance_id.num')
    mi_old_num = fields.Char(related='medical_insurance_id.old_num')
    mi_insurance_type = fields.Selection(related='medical_insurance_id.insurance_type')
    mi_injury_person_num = fields.Char(related='medical_insurance_id.injury_person_num')
    mi_injury_company_num = fields.Char(related='medical_insurance_id.injury_company_num')
    mi_name = fields.Char(related='medical_insurance_id.name')
    mi_gender = fields.Char(related='medical_insurance_id.gender')
    mi_age = fields.Char(related='medical_insurance_id.age')
    mi_identity_id = fields.Many2one(related='medical_insurance_id.identity_id')
    mi_nation = fields.Char(related='medical_insurance_id.nation')
    mi_address = fields.Char(related='medical_insurance_id.address')
    mi_personnel_type = fields.Selection(related='medical_insurance_id.personnel_type')

    # 患者基础信息
    marriage = fields.Selection([('0', '未婚'), ('1', '已婚')], '婚姻', default='0')
    married_age = fields.Char('结婚年龄')

    bear = fields.Selection([('0', '未生育'), ('1', '已生育')], '生育', default='0')
    bear_age = fields.Char('生育年龄')
    boy_count = fields.Integer('几子')
    girl_count = fields.Integer('几女')

    hypertension = fields.Char('高血压')
    hepatitis = fields.Char('肝炎')
    coronary_heart = fields.Char('冠心病')
    tuberculosis = fields.Char('结核')
    diabetes = fields.Char('糖尿病')
    operation = fields.Char('手术史')
    allergy = fields.Char('过敏史')

    smoke = fields.Char('吸烟史')
    drink = fields.Char('饮酒史')

    menstruation = fields.Char('月经史')

    inheritance = fields.Char('家族遗传史')

    _sql_constraints = [
        ('partner_code_uniq', 'unique(code)', 'GLEKE编码不能重复 !'),
        ('identity_no_uniq', 'unique(identity_no)', '身份证不能重复 !'),
    ]

    @api.multi
    def name_get(self):
        result = []
        for partner in self:
            name = '%s(%s)' % (partner.name, partner.code) if partner.code else partner.name
            result.append((partner.id, name))
        return result

    @api.multi
    def get_formview_id(self):
        return self.env.ref('shango_app.app_partner_form_view').id

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        if view_type == 'form' and self.env.context.get('app_contact'):
            view_id = self.env.ref('shango_app.view_app_contact_form').id
        return super(Partner, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

    @api.model
    def default_get(self, fields_list):
        res = super(Partner, self).default_get(fields_list)
        context = self._context
        if context.get('customer'):
            res.update({'is_patient': True})
        if context.get('is_patient'):
            res.update({'customer': False, 'is_patient': True})
        if context.get('is_doctor'):
            res.update({'customer': False, 'is_doctor': True})
        if context.get('patient_property'):
            res.update({'customer': False, 'patient_property': context['patient_property']})

        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        domain = ['|', ('code', operator, name), ('name', operator, name)]
        args = args or []
        if self._context.get('relationship') == 'self':
            domain += [('id', '=', self._context['relation_parent_id'])]
        partners = self.search(args + domain, limit=limit)
        return partners.name_get()

    # @api.model
    # def create(self, vals):
    #     self.check_mobile_and_identity(vals)
    #     return super(Partner, self).create(vals)

    # @api.multi
    # def write(self, vals):
    #     self.check_mobile_and_identity(vals)
    #     return super(Partner, self).write(vals)

    # @staticmethod
    # def check_mobile_and_identity(vals):
    #     if vals.get('phone'):
    #         if not Partner.check_mobile(vals['phone']):
    #             raise Warning('请填写正确的手机号')
    #     if vals.get('identity_no'):
    #         if not Partner.check_identity(vals['identity_no']):
    #             raise Warning('请填写正确的身份证号')

    # @staticmethod
    # def check_mobile(mobile):
    #     """验证手机号码"""
    #     mobile_pattern_str = config['mobile_pattern_str']
    #
    #     phone_pattern = re.compile(r'^' + mobile_pattern_str + '$')
    #     phone_group = phone_pattern.match(mobile)
    #     if not phone_group:
    #         return False
    #     return True

    # @staticmethod
    # def check_identity(identity_no):
    #     """验证身份证"""
    #     identity_pattern_str = config['identity_pattern_str']
    #
    #     identity_pattern = re.compile(r'^' + identity_pattern_str + '$')
    #     id_group = identity_pattern.match(identity_no)
    #     if not id_group:
    #         return False
    #     return True

    @staticmethod
    def compute_newborn_age(birthday):
        """计算新生儿年龄"""
        today = datetime.strptime(datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT), DEFAULT_SERVER_DATE_FORMAT)  # 当前日期
        birthday = datetime.strptime(birthday, DEFAULT_SERVER_DATE_FORMAT)  # 出生日期
        ages = relativedelta(today, birthday)  # 新生儿年龄
        return ages

    @api.multi
    def _compute_age(self):
        for record in self:
            if record.birth_date:
                ages = self.compute_newborn_age(record.birth_date)  # 计算新生儿年龄
                record.age = u'%d岁' % (ages.years + 1)

    @api.multi
    def _compute_month_label(self):
        for partner in self:
            if not partner.birth_date:
                continue

            ages = self.compute_newborn_age(partner.birth_date)  # 计算新生儿年龄
            months = ages.years * 12 + ages.months  # 出生到现在月数
            if not months:
                partner.month_label = '%d天' % ages.days
            elif not ages.years:
                partner.month_label = '%d个月+%d天' % (ages.months, ages.days) if ages.days else '%d个月' % ages.months
            else:
                if ages.years >= 7:
                    partner.month_label = '%d周岁' % ages.years
                else:
                    if not ages.months:
                        partner.month_label = '%d周岁' % ages.years
                    elif ages.months == 6:
                        partner.month_label = '%d岁半' % ages.years
                    else:
                        partner.month_label = '%d岁%d个月' % (ages.years, ages.months)

    # @api.onchange('identity_no')
    # def onchange_identity_no(self):
    #     if self.identity_no:
    #         if not self.check_identity(self.identity_no):  # 验证身份证
    #             raise Warning('身份证号错误!')
    #         else:
    #             self.birth_date = '%s-%s-%s' % (
    #                 self.identity_no[6:10], self.identity_no[10:12], self.identity_no[12:14])
    #     else:
    #         self.birth_date = False