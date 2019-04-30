# -*- coding: utf-8 -*-
from odoo import models, fields


class HrpInoculationCycle(models.Model):

    _name = 'hrp.inoculation_cycle'
    _description = u'接种周期'

    name = fields.Char('名称')

