# -*- coding: utf-8 -*-
from odoo import models, fields


class HrpInoculationRecord(models.Model):

    _name = 'hrp.inoculation_record'
    _description = u'接种记录'

    partner_id = fields.Many2one('res.partner', '患者')
    inoculate_time = fields.Datetime('接种时间')
    is_private = fields.Boolean('是否自费')
    company_id = fields.Many2one('res.company', '接种医院')
    doctor = fields.Char('接种医生')
    item_id = fields.Many2one('hrp.inoculation_item', '接种项目')
    schedule_id = fields.Many2one('hrp.inoculation_schedule', '接种计划')
    vaccine_manufacturer = fields.Char('疫苗厂商')
    batch_number = fields.Char('批次号')
