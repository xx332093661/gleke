# -*- encoding:utf-8 -*-
from odoo import fields, models, api


class ConvenientItem(models.Model):
    _name = 'his.convenient_item'
    _description = '便民服务项目'
    update_external = True  # 更新外部服务器数据


    category_id = fields.Many2one('his.convenient_service_category', '分类', ondelete='cascade')
    name = fields.Char('项目名称')
    department_id = fields.Many2one('hr.department', '执行科室')
    image = fields.Binary('图片')
    description = fields.Text('项目描述')
    content = fields.Text('项目内容')
    detail_ids = fields.One2many('his.convenient_item_detail', 'item_id', '项目详情')
    start_months = fields.Integer('开始月龄')
    end_months = fields.Integer('截止月龄')
    term = fields.Integer('消费期限', help='单位：月')
    is_package = fields.Boolean('打包购买', default=lambda self: True if self.env.context['category_code'] in ['inspection', 'checkout', 'physical'] else False)
    discount = fields.Float('折扣', default=100)
    quantity = fields.Integer('数量', default=1)

    package_detail_ids = fields.One2many('his.convenient_item_package_detail', 'item_id', '套餐明细')
    fee_ids = fields.One2many('his.convenient_item_package_detail_fee', 'item_id', '关联收费')
    item_product_ids = fields.One2many('his.convenient_item_product', 'item_id', 'OTC药品')

    item_price = fields.Float('项目收费', compute='_compute_item_price')

    @api.multi
    def _compute_item_price(self):
        for record in self:
            if record.category_id.code == 'service': # 服务项目
                record.item_price = sum([detail.item_price for detail in record.package_detail_ids]) * record.quantity * record.discount / 100
                # if record.is_package: # 是套餐
                #     record.item_price = sum([detail.item_price for detail in record.package_detail_ids]) * record.quantity * record.discount / 100
                # else:
                #     record.item_price = sum([fee.price_subtotal for fee in record.fee_ids]) * record.quantity * record.discount / 100

            if record.category_id.code in ['medicine', 'inspection', 'checkout']: # 药品
                record.item_price = sum([fee.price_subtotal for fee in record.fee_ids]) * record.quantity * record.discount / 100
                # if record.is_package: # 打包购买
                #     record.item_price = sum([fee.price_subtotal for fee in record.fee_ids]) * record.quantity * record.discount / 100
                # else:
                #     record.item_price = 0

            if record.category_id.code == 'physical': # 体检
                record.item_price = sum([detail.item_price for detail in record.package_detail_ids]) * record.quantity * record.discount / 100


    @api.onchange('category_id')
    def onchange_category_id(self):
        if self.env.context.get('change_name') and not self.name:
            self.name = self.category_id.name


    # @api.onchange('is_package')
    # def onchange_is_package(self):
    #     self.package_detail_ids = [(6, 0, [])]
    #     self.fee_ids = [(6, 0, [])]
    #     self.item_product_ids = [(6, 0, [])]
    #     self.discount = 100
    #     self.quantity = 1

    @api.onchange('discount', 'quantity', 'package_detail_ids', 'fee_ids')
    def onchange_discount_quantity(self):
        category_code = self.env.context['category_code']
        if category_code == 'service': # 服务项目
            self.item_price = sum(
                [detail.item_price for detail in self.package_detail_ids]) * self.quantity * self.discount / 100
            # if self.is_package:
            #     self.item_price = sum([detail.item_price for detail in self.package_detail_ids]) * self.quantity * self.discount / 100
            # else:
            #     self.item_price = sum([fee.price_subtotal for fee in self.fee_ids]) * self.quantity * self.discount / 100

        if category_code in ['medicine', 'inspection', 'checkout']:  # 药品
            self.item_price = sum([fee.price_subtotal for fee in self.fee_ids]) * self.quantity * self.discount / 100
            # if self.is_package: # 打包购买
            #     self.item_price = sum([fee.price_subtotal for fee in self.fee_ids]) * self.quantity * self.discount / 100
            # else:
            #     self.item_price = 0

        if category_code == 'physical':  # 服务项目
            self.item_price = sum([detail.item_price for detail in self.package_detail_ids]) * self.quantity * self.discount / 100


class ConvenientItemPackageDetail(models.Model):
    _name = 'his.convenient_item_package_detail'
    _description = '套餐明细'
    update_external = True  # 更新外部服务器数据

    item_id = fields.Many2one('his.convenient_item', '便民项目', ondelete='cascade')
    name = fields.Char('诊疗项目名称')
    code = fields.Char('诊疗项目编码')
    remark = fields.Char('说明')
    department_id = fields.Many2one('hr.department', '执行科室')
    quantity = fields.Integer('数量', default=1)
    item_price = fields.Float('收费', compute='_compute_item_price')
    fee_ids = fields.One2many('his.convenient_item_package_detail_fee', 'detail_id', '关联收费')

    @api.multi
    def _compute_item_price(self):
        for record in self:
            record.item_price = sum([fee.price_subtotal for fee in record.fee_ids]) * record.quantity

    @api.onchange('fee_ids', 'quantity')
    def onchange_fee_ids(self):
        self.item_price = sum([fee.price_subtotal for fee in self.fee_ids]) * self.quantity


class ConvenientItemPackageDetailFee(models.Model):
    _name = 'his.convenient_item_package_detail_fee'
    _description = '关联收费'
    update_external = True  # 更新外部服务器数据

    detail_id = fields.Many2one('his.convenient_item_package_detail', '套餐明细', ondelete='cascade')
    item_id = fields.Many2one('his.convenient_item', '便民项目', ondelete='cascade')
    product_id = fields.Many2one('product.template', '对应收费', ondelete='cascade')
    uom_id = fields.Many2one('product.uom', '单位', related='product_id.uom_id')
    list_price = fields.Float('单价', related='product_id.list_price')

    scale = fields.Integer('收费系数', default=1)
    price_subtotal = fields.Float('小计', compute='_compute_price_subtotal')


    @api.multi
    def _compute_price_subtotal(self):
        for record in self:
            record.price_subtotal = record.list_price * record.scale


    @api.onchange('list_price', 'scale')
    def onchange_list_price_scale(self):
        self.price_subtotal = self.list_price * self.scale


class ConvenientItemProduct(models.Model):
    _name = 'his.convenient_item_product'
    _description = '便民服务关联的产品'
    update_external = True  # 更新外部服务器数据

    item_id = fields.Many2one('his.convenient_item', '便民项目', ondelete='cascade')
    product_id = fields.Many2one('product.template', '对应收费', ondelete='cascade')
    uom_id = fields.Many2one('product.uom', '单位', related='product_id.uom_id')
    list_price = fields.Float('单价', related='product_id.list_price')


class ConvenientItemDetail(models.Model):
    _name = 'his.convenient_item_detail'
    _description = '便民服务详情'
    _rec_name = 'id'
    update_external = True  # 更新外部服务器数据

    item_id = fields.Many2one('his.convenient_item', '便民项目', ondelete='cascade')
    description = fields.Text('详情描述')
    image = fields.Binary('图片')






