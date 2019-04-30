# -*- coding: utf-8 -*-
from odoo import models, fields


class HrpInoculationItem(models.Model):

    _name = 'hrp.inoculation_item'
    _description = u'接种项目'

    name = fields.Char('名称')
    prevent_disease = fields.Char('预防疾病')
    part = fields.Char('接种部位')
    method = fields.Char('接种方法')
    effect = fields.Text('接种效果')
    taboo = fields.Text('禁忌')
    attention = fields.Text('注意事项')
    reaction = fields.Text('可能反应')
    is_private = fields.Boolean('是否自费')
    times = fields.Integer('接种总次数')
    product_ids = fields.Many2many('product.template', 'inoculation_item_product_rel', 'item_id', 'product_id', '产品')
