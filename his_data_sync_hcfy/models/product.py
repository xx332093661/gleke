# -*- encoding:utf-8 -*-
from odoo import api
from odoo import models, fields



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    code = fields.Char('编码')
    fee_name = fields.Char('收据费目')
    his_id = fields.Integer('HISID', index=True)


    @api.model
    def his_id_exist(self, his_id):
        return self.search([('his_id', '=', his_id)])

    @api.model
    def create(self, vals):
        # TODO 测试用
        if not vals.get('his_id'):
            vals['his_id'] = -1

        product = self.his_id_exist(vals['his_id'])
        if not product:
            return super(ProductTemplate, self).create(vals)

        if product.list_price != vals['list_price']:
            product.list_price = vals['list_price']

        return product


