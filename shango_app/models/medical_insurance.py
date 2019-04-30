# -*- coding: utf-8 -*-
from odoo import models, fields


class HrpMedicalInsurance(models.Model):

    _name = 'hrp.medical_insurance'
    _description = u'医保卡'

    num = fields.Char('社保卡号')
    old_num = fields.Char('老社保卡号')
    insurance_type = fields.Selection([('1', '医疗保险'), ('2', '工伤保险'), ('1', '生育保险')], '险种类别')
    injury_person_num = fields.Char('工伤个人编号')
    injury_company_num = fields.Char('工伤单位编号')
    name = fields.Char('姓名')
    gender = fields.Char('性别')
    age = fields.Char('实足年龄')
    identity_id = fields.Many2one('hrp.identity', '身份证')
    nation = fields.Char('民族')
    address = fields.Char('住址')
    personnel_type = fields.Selection([('11', '在职'), ('21', '退休'), ('41', '成年人')], '人员类别')

    _rec_name = 'num'
