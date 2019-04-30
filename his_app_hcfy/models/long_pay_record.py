# -*- coding: utf-8 -*-
from odoo import models, fields
import hashlib


class HisLongPayRecord(models.Model):

    _name = 'his.long_pay_record'
    _description = u'龙支付记录'

    POSID = fields.Char('商户柜台代码')
    BRANCHID = fields.Char('分行代码')
    ORDERID = fields.Char('定单号')
    PAYMENT = fields.Char('付款金额')
    CURCODE = fields.Char('币种')
    REMARK1 = fields.Char('备注一')
    REMARK2 = fields.Char('备注二')
    ACC_TYPE = fields.Char('账户类型')
    SUCCESS = fields.Char('成功标志')
    TYPE = fields.Char('接口类型')
    REFERER = fields.Char('Referer信息')
    CLIENTIP = fields.Char('客户端IP')
    ACCDATE = fields.Char('系统记账日期')
    USRMSG = fields.Char('支付账户信息')
    INSTALLNUM = fields.Char('分期期数')
    ERRMSG = fields.Char('错误信息')
    USRINFO = fields.Char('客户加密信息')
    DISCOUNT = fields.Char('优惠金额')
    SIGN = fields.Char('数字签名')

    is_refund = fields.Boolean('是否退款')
    refund_time = fields.Datetime('退款时间')
    refund_code = fields.Char('退款状态码')
    refund_msg = fields.Char('退款返回信息')

    order_ids = fields.Many2many('sale.order', 'long_pay_record_order_rel', 'record_id', 'order_id', '订单')



