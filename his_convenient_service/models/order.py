# -*- encoding:utf-8 -*-
from odoo import models, fields


class Order(models.Model):
    _inherit = 'sale.order'

    convenient_item_id = fields.Many2one('his.convenient_item', '便民服务项目')

