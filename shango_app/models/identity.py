# -*- coding: utf-8 -*-
from odoo import models, fields


class HrpIdentity(models.Model):
    _name = 'hrp.identity'
    _description = u'身份证'

    identity_num = fields.Char('身份证号')
    name = fields.Char('姓名')
    gender = fields.Char('性别')
    nation = fields.Char('民族')
    birth_date = fields.Date('出生日期')
    address = fields.Char('住址')

    _rec_name = 'identity_num'
