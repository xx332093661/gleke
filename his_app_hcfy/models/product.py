# -*- encoding:utf-8 -*-
from odoo import models, api


class ProductCategory(models.Model):
    _inherit = 'product.category'
    update_external = True  # 更新外部服务器数据


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    update_external = True  # 更新外部服务器数据

    # @api.model
    # def create(self, vals):
    #     if self.env.context.get('create_recharge'):
    #         product_category = self.env['ir.model.data'].sudo().get_object('his_app_hcfy', 'product_category_recharge')
    #         product = self.search([], limit=1, order='his_id asc')
    #         if product.his_id > 0:
    #             his_id = -1
    #         else:
    #             his_id = product.his_id - 1
    #         vals.update({
    #             'name': '充值%s元' % str(vals['list_price']),
    #             'categ_id': product_category.id,
    #             'type': 'service',
    #             'his_id': his_id
    #         })
    #
    #     return super(ProductTemplate, self).create(vals)
    #
    # @api.multi
    # def write(self, vals):
    #     if self.env.context.get('create_recharge') and 'list_price' in vals:
    #         vals.update({
    #             'name': '充值%s元' % str(vals['list_price']),
    #         })
    #     return super(ProductTemplate, self).write(vals)


class ProductUomCateg(models.Model):
    _inherit = 'product.uom.categ'
    update_external = True  # 更新外部服务器数据


class ProductUom(models.Model):
    _inherit = 'product.uom'
    update_external = True  # 更新外部服务器数据

