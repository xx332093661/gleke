# -*- coding: utf-8 -*-
from odoo import models, fields


class HrpPatient(models.Model):
    _name = 'hrp.patient'
    _description = u'患者'

    # name = fields.Char('姓名')
    partner_id = fields.Many2one('res.partner', '伙伴')
    company_id = fields.Many2one('res.company', '医院')
    internal_id = fields.Integer('内部id')
    # phone = fields.Char('电话')
    # identity_id = fields.Char('身份证')
    # medical_insurance = fields.Char('医保')
    card_no = fields.Char('就诊卡')
    medical_card = fields.Char('医保卡')
    outpatient_num = fields.Char('门诊号')

    openid = fields.Char('openid')
