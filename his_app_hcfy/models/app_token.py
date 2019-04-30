# -*- encoding:utf-8 -*-
from odoo import fields, models


class AppToken(models.Model):
    _name = 'his.app_token'
    _description = 'App令牌'

    mac = fields.Char('MAC')
    token = fields.Char('令牌')

