# -*- encoding:utf-8 -*-
from odoo import models, fields


class SubscribeType(models.Model):
    _name = 'his.subscribe_type'
    _description = 'Oracle订阅类型'

    name = fields.Char('名称', required=True)
    subscribe_type = fields.Selection([('OPCODE_INSERT', '插入'), ('OPCODE_UPDATE', '更新')], '类型')

