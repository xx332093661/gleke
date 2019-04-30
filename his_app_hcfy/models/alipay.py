# -*- coding: utf-8 -*-
from odoo import models, fields


class AlipayRecord(models.Model):
    _name = 'his.alipay_record'
    _description = u'支付宝支付记录'
    _order = 'id desc'


    notify_time = fields.Char('通知时间')
    notify_type = fields.Char('通知类型')
    notify_id = fields.Char('通知校验ID')
    app_id = fields.Char('应用Id')
    charset = fields.Char('编码格式')
    version = fields.Char('接口版本')
    sign_type = fields.Char('签名类型')
    sign = fields.Char('签名')
    trade_no = fields.Char('支付宝交易号')
    out_trade_no = fields.Char('商户订单号')
    trade_status = fields.Char('交易状态')
    total_amount = fields.Float('订单金额')
    receipt_amount = fields.Float('实收金额')
    buyer_pay_amount = fields.Float('付款金额')
    gmt_create = fields.Char('交易创建时间')
    gmt_payment = fields.Char('交易付款时间')
    gmt_close = fields.Char('交易结束时间')
    passback_params = fields.Char('回传参数')
    tran_flow = fields.Char('医院流水号')


    # 退款
    is_refund = fields.Boolean('是否退款')
    refund_time = fields.Datetime('退款时间')
    refund_code = fields.Char('退款状态码')
    refund_msg = fields.Char('退款返回信息')

    order_ids = fields.Many2many('sale.order', 'his_alipay_order_rel', 'alipay_id', 'order_id', '订单')
