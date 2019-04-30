# -*- encoding:utf-8 -*-
from odoo import models, fields



class HrpBusiness(models.Model):
    _inherit = 'hrp.business'


    clinic_item_ids = fields.One2many('his.clinic_item_category', 'business_id', '诊疗项目目录')


