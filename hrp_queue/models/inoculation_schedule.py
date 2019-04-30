# -*- coding: utf-8 -*-
from odoo import models, fields


class HrpInoculationSchedule(models.Model):

    _name = 'hrp.inoculation_schedule'
    _description = u'接种计划'

    item_id = fields.Many2one('hrp.inoculation_item', '接种项目')
    cycle_id = fields.Many2one('hrp.inoculation_cycle', '接种周期')
    agent_count = fields.Integer('剂数')
    necessary = fields.Boolean('是否必打')


class HrpInoculationPersonalSchedule(models.Model):

    _name = 'hrp.inoculation_personal_schedule'
    _description = u'个人接种计划'

    partner_id = fields.Many2one('res.partner', '患者')
    item_id = fields.Many2one('hrp.inoculation_item', '接种项目')
    cycle_id = fields.Many2one('hrp.inoculation_cycle', '接种周期')
    agent_count = fields.Integer('剂数')
    necessary = fields.Boolean('是否必打')