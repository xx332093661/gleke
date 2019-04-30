# -*- encoding:utf-8 -*-
from odoo import fields, models


class RefundApply(models.Model):
    _name = 'his.refund_apply'
    _description = '退款申请'
    _order = 'id desc'

    # partner_id = fields.Many2one('res.partner', '退款人')
    visit_partner_id = fields.Many2one('res.partner', '就诊人')

    pay_method = fields.Selection([('weixin', '微信支付'), ('alipay', '支付宝支付'), ('longpay', '龙支付')], '支付方式')
    order_type = fields.Selection([('register', '挂号'), ('payment', '缴费'), ('recharge', '充值'), ('service', '便民服务')], '订单类别')
    amount_total = fields.Float('退款金额')
    trade_no = fields.Char('支付宝交易号')
    transaction_id = fields.Char('微信支付订单号')
    reason = fields.Char('退款原因')
    refund_time = fields.Datetime('退款时间')
    state = fields.Selection([('draft', '申请'), ('done', '完成')], '状态')

    alipay_ids = fields.Many2many('his.alipay_record', 'his_refund_apply_alipay_rel', 'refund_apply_id', 'alipay_id', '支付宝支付记录')
    weixin_pay_ids = fields.Many2many('his.weixin_pay_record', 'his_pay_refund_apply_weixin_rel', 'refund_apply_id', 'weixin_pay_id', '微信支付记录')
    long_pay_record_ids = fields.Many2many('his.long_pay_record', 'his_pay_refund_apply_longpay_rel', 'refund_apply_id', 'longpay_id', '龙支付记录')

    order_ids = fields.Many2many('sale.order', 'his_refund_apply_order_rel', 'refund_apply_id', 'order_id', '订单')














