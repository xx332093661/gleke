# -*- coding: utf-8 -*-
from odoo import models, fields


class WeixinPayRecord(models.Model):
    _name = 'his.weixin_pay_record'
    _description = u'微信支付记录'
    _order = 'id desc'

    return_code = fields.Char('返回状态码')
    return_msg = fields.Char('返回信息')

    # 以下字段在return_code为SUCCESS的时候有返回
    appid = fields.Char('应用ID')
    mch_id = fields.Char('商户号')

    device_info = fields.Char('设备号')
    nonce_str = fields.Char('随机字符串')
    sign = fields.Char('签名')

    result_code = fields.Char('业务结果')
    err_code = fields.Char('错误代码')
    err_code_des = fields.Char('错误代码描述')

    openid = fields.Char('用户标识')

    is_subscribe = fields.Char('是否关注公众账号')
    trade_type = fields.Char('交易类型')
    bank_type = fields.Char('付款银行')

    total_fee = fields.Char('总金额')

    fee_type = fields.Char('货币种类')
    cash_fee = fields.Char('现金支付金额')
    cash_fee_type = fields.Char('现金支付货币类型')
    coupon_fee = fields.Char('代金券或立减优惠金额')
    coupon_count = fields.Char('代金券或立减优惠使用数量')
    coupon_id_n = fields.Char('代金券或立减优惠ID')
    coupon_fee_n = fields.Char('单个代金券或立减优惠支付金额')
    transaction_id = fields.Char('微信支付订单号')
    out_trade_no = fields.Char('商户订单号')
    attach = fields.Char('商家数据包')

    time_end = fields.Char('支付完成时间')
    tran_flow = fields.Char('医院流水号')

    # 退款
    is_refund = fields.Boolean('是否退款')
    refund_time = fields.Datetime('退款时间')
    refund_code = fields.Char('退款状态码')
    refund_msg = fields.Char('退款返回信息')


    order_ids = fields.Many2many('sale.order', 'his_weixin_pay_order_rel', 'weixin_pay_id', 'order_id', '订单')