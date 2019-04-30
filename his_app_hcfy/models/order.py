# -*- encoding:utf-8 -*-
from odoo import fields, models


class Order(models.Model):
    _inherit = 'sale.order'

    pay_method = fields.Selection([('weixin', '微信'), ('alipay', '支付宝'), ('longpay', '龙支付'), ('free', '免费'), ('coupon', '卷支付')], '支付方式')
    order_type = fields.Selection([('register', '挂号'), ('payment', '缴费'), ('recharge', '充值'), ('service', '便民服务')], '订单类别')
    recharge_type = fields.Selection([('1', '门诊'), ('2', '住院')], '充值类型')
    receipt_no = fields.Char('单据号')

    tran_flow = fields.Char('医院结算流水号')
    commit_his_state = fields.Selection([('-1', '未提交'), ('0', '提交HIS失败'), ('1', '提交HIS成功')], '提交HIS状态', default='-1')
    commit_his_error_msg = fields.Char('提交HIS错误信息')
    is_refund = fields.Boolean('是否退款')
    refund_time = fields.Datetime('退款时间')


    reserve_record_ids = fields.One2many('his.reserve_record', 'order_id', '预约记录')

    alipay_ids = fields.Many2many('his.alipay_record', 'his_alipay_order_rel', 'order_id', 'alipay_id', '支付宝支付记录')
    weixin_pay_ids = fields.Many2many('his.weixin_pay_record', 'his_weixin_pay_order_rel', 'order_id', 'weixin_pay_id', '微信支付记录')
    long_pay_record_ids = fields.Many2many('his.long_pay_record', 'long_pay_record_order_rel', 'order_id', 'record_id', '龙支付记录')


class OrderLine(models.Model):
    _inherit = 'sale.order.line'

    fee_name = fields.Char('收据费目')
