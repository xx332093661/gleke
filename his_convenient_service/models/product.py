# -*- encoding:utf-8 -*-
from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        print self.env.context
        package_detail_fee_obj = self.env['his.convenient_item_package_detail_fee'] # 套餐明细关联收费
        item_product_obj = self.env['his.convenient_item_product'] # 关联产品

        # 套餐明细关联收费
        if self.env.context.get('fee_ids'):
            exist = []
            for line in self.env.context['fee_ids']:
                if line[0] == 4:
                    package_detail_fee = package_detail_fee_obj.browse(line[1])
                    exist.append(package_detail_fee.product_id.id)

                if line[0] == 0:
                    exist.append(line[2]['product_id'])

            if exist:
                args += [('id', 'not in', exist)]

        # 关联产品
        if self.env.context.get('item_product_ids'):
            exist = []
            for line in self.env.context['item_product_ids']:
                if line[0] == 4:
                    item_product = item_product_obj.browse(line[1])
                    exist.append(item_product.product_id.id)
                if line[0] == 0:
                    exist.append(line[2]['product_id'])

            if exist:
                args += [('id', 'not in', exist)]

        return super(ProductTemplate, self).name_search(name=name, args=args, operator=operator, limit=limit)



