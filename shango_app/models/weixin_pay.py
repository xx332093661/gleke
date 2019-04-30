# -*- coding: utf-8 -*-
from odoo import models, fields
from ..models.emqtt import Emqtt

import uuid


class HisWeixinPayRecord(models.Model):

    _name = 'his.weixin_pay_record'
    _description = u'微信支付记录'

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

    total_fee = fields.Integer('总金额')

    fee_type = fields.Char('货币种类')
    cash_fee = fields.Integer('现金支付金额')
    cash_fee_type = fields.Char('现金支付货币类型')
    transaction_id = fields.Char('微信支付订单号')
    out_trade_no = fields.Char('商户订单号')
    attach = fields.Char('商家数据包')

    time_end = fields.Char('支付完成时间')

    is_refund = fields.Boolean('是否退款')
    refund_time = fields.Datetime('退款时间')
    refund_code = fields.Char('退款状态码')
    refund_msg = fields.Char('退款返回信息')

    order_ids = fields.Many2many('sale.order', 'his_weixin_pay_order_rel', 'weixin_pay_id', 'order_id', '订单')

    company_id = fields.Many2one('res.company', '医院')
    internal_id = fields.Integer('内部id')
