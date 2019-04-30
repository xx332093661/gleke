# -*- coding: utf-8 -*-
from odoo import models, fields


class Order(models.Model):
    _inherit = 'sale.order'

    internal_id = fields.Integer('内部id')

    pay_method = fields.Selection([('weixin', '微信支付'), ('alipay', '支付宝支付'), ('longpay', '龙支付'), ('coupon', '券支付'), ('free', '免费')], '支付方式')
    order_type = fields.Selection([('register', '预约挂号'), ('payment', '缴费'), ('recharge', '充值'), ('service', '便民服务')], '订单类型')
    recharge_type = fields.Selection([('1', '门诊'), ('2', '住院')], '充值类型')
    visit_partner_id = fields.Many2one('res.partner', '就诊人')
    receipt_no = fields.Char('单据号')
    commit_his_state = fields.Selection([('-1', '未提交'), ('0', '提交HIS失败'), ('1', '提交HIS成功')], '提交HIS状态', default='-1')
    commit_his_error_msg = fields.Char('提交HIS错误信息')

    mz_balance = fields.Float('门诊帐户余额')
    zy_balance = fields.Float('住院帐户余额')

    alipay_ids = fields.Many2many('his.alipay_record', 'his_alipay_order_rel', 'order_id', 'alipay_id', '支付宝支付记录')
    weixin_pay_ids = fields.Many2many('his.weixin_pay_record', 'his_weixin_pay_order_rel', 'order_id', 'weixin_pay_id', '微信支付记录')
    long_pay_record_ids = fields.Many2many('his.long_pay_record', 'long_pay_record_order_rel', 'order_id', 'record_id', '龙支付记录')

    is_refund = fields.Boolean('是否退款')
    refund_time = fields.Datetime('退款时间')

    def create_order(self, partner_id, company_id, products, pay_method, order_type):
        """创建订单"""
        order_lines = []
        if pay_method not in ['free', 'coupon']:
            for product in products:
                order_line = (0, 0, {
                    'product_id': product.id,
                    'name': product.name,
                    'product_uom_qty': 1,
                    'price_unit': product.list_price,
                    'product_uom': product.uom_id.id,
                    'tax_id': False,
                })
                order_lines.append(order_line)
        # 创建订单
        order = self.create({
            'partner_id': partner_id,
            'order_line': order_lines,
            'company_id': company_id,
            'pay_method': pay_method,
            'order_type': order_type,
        })
        return order


class OrderLine(models.Model):
    _inherit = 'sale.order.line'

    fee_name = fields.Char('收据费目')

