# -*- encoding:utf-8 -*-
from odoo import models, fields



class HrpQueue(models.Model):
    _inherit = 'hrp.queue'

    origin_table = fields.Char('来源表')
    origin_id = fields.Integer('来源ID')


