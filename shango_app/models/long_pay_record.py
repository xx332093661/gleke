# -*- coding: utf-8 -*-
from odoo import models, fields
from collections import OrderedDict

import hashlib
import urllib
import execjs


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

    company_id = fields.Many2one('res.company', '医院')
    internal_id = fields.Integer('内部ID')

    def get_pay_parameter(self, company, orders):
        """获取支付参数"""
        def md5_encode(str):
            m = hashlib.md5()
            m.update(str)
            return m.hexdigest()

        if not orders:
            return

        amount_total = round(sum([order.amount_total for order in orders]), 2)  # 订单总额
        attach = '|'.join([order.name for order in orders])  # 附加数据包
        pub = company.long_key[-30:]


        reginfo = '测试注册信息'
        proinfo = orders[0].order_line[0].product_id.name if orders[0].order_line else '未知'

        reginfo = execjs.eval("""escape('%s')""" % reginfo)
        proinfo = execjs.eval("""escape('%s')""" % proinfo)

        # 'MERCHANTID': company.long_mch_id,  # 商户代码
        # 'POSID': company.long_counter_id,  # 商户柜台代码
        # 'BRANCHID': company.long_branch_code,  # 分行代码
        # 'ORDERID': orders[0].name,  # 定单号
        # 'PAYMENT': orders[0].amount_total,  # 付款金额
        # 'CURCODE': '01',  # 币种
        # 'TXCODE': '520100',  # 交易码
        # 'MAC': '',  # MAC校验域
        # 'TYPE': '1',  # 接口类型
        # 'PUB': '',  # 公钥后30位
        # 'GATEWAY': 'UnionPay',  # 网关类型

        # o = OrderedDict()
        # o['MERCHANTID'] = company.long_mch_id
        # o['POSID'] = company.long_counter_id
        # o['BRANCHID'] = company.long_branch_code
        # o['ORDERID'] = orders[0].name
        # o['PAYMENT'] = amount_total
        # o['CURCODE'] = '01'
        # o['TXCODE'] = '520100'
        # o['REMARK1'] = 'remark1'
        # o['REMARK2'] = 'remark2'
        # o['TYPE'] = '1'
        # o['PUB'] = pub
        # o['GATEWAY'] = 'test'
        # o['CLIENTIP'] = '127.0.0.1'
        # o['REGINFO'] = 'cs'
        # o['PROINFO'] = 'cs'
        # o['REFERER'] = '121.201.68.100'
        # o['THIRDAPPINFO'] = 'comccbpay' + company.long_mch_id + 'glekePay'
        #
        # o2 = OrderedDict()
        # o2['MERCHANTID'] = company.long_mch_id
        # o2['POSID'] = company.long_counter_id
        # o2['BRANCHID'] = company.long_branch_code
        # o2['ORDERID'] = orders[0].name
        # o2['PAYMENT'] = amount_total
        # o2['CURCODE'] = '01'
        # o2['TXCODE'] = '520100'
        # o2['REMARK1'] = 'remark1'
        # o2['REMARK2'] = 'remark2'
        # o2['TYPE'] = '1'
        # o2['GATEWAY'] = 'test'
        # o2['CLIENTIP'] = '127.0.0.1'
        # o2['REGINFO'] = 'cs'
        # o2['PROINFO'] = 'cs'
        # o2['REFERER'] = '121.201.68.100'
        # o2['THIRDAPPINFO'] = 'comccbpay' + company.long_mch_id + 'glekePay'
        #
        # parameter1 = urllib.urlencode(o)  # 加密用
        # parameter2 = urllib.urlencode(o2)  # 请求用


        parameter1 = "MERCHANTID=" + company.long_mch_id + "&" + \
                     "POSID=" + company.long_counter_id + "&" + \
                     "BRANCHID=" + company.long_branch_code + "&" + \
                     "ORDERID=" + orders[0].name + "&" + \
                     "PAYMENT=" + str(amount_total) + "&" + \
                     "CURCODE=" + '01' + "&" + \
                     "TXCODE=" + '520100' + "&" + \
                     "REMARK1=" + 'remark1' + "&" + \
                     "REMARK2=" + 'remark2' + "&" + \
                     "TYPE=" + '1' + "&" + \
                     "PUB=" + pub + "&" + \
                     "GATEWAY=" + 'test' + '&' + \
                     "CLIENTIP=" + '127.0.0.1' + '&' + \
                     "REGINFO=" + reginfo + '&' + \
                     "PROINFO=" + proinfo + '&' + \
                     "REFERER=" + '121.201.68.100' + '&' + \
                     "THIRDAPPINFO=" + 'comccbpay' + company.long_mch_id + 'glekePay'

        parameter2 = "MERCHANTID=" + company.long_mch_id + "&" + \
                     "POSID=" + company.long_counter_id + "&" + \
                     "BRANCHID=" + company.long_branch_code + "&" + \
                     "ORDERID=" + orders[0].name + "&" + \
                     "PAYMENT=" + str(amount_total) + "&" + \
                     "CURCODE=" + '01' + "&" + \
                     "TXCODE=" + '520100' + "&" + \
                     "REMARK1=" + 'remark1' + "&" + \
                     "REMARK2=" + 'remark2' + "&" + \
                     "TYPE=" + '1' + "&" + \
                     "GATEWAY=" + 'test' + '&' + \
                     "CLIENTIP=" + '127.0.0.1' + '&' + \
                     "REGINFO=" + reginfo + '&' + \
                     "PROINFO=" + proinfo + '&' + \
                     "REFERER=" + '121.201.68.100' + '&' + \
                     "THIRDAPPINFO=" + 'comccbpay' + company.long_mch_id + 'glekePay'

        mac = md5_encode(parameter1)  # 参数生成MAC

        parameter = parameter2 + "&" + "MAC=" + mac  # 将生成的MAC拼接到原参数后面

        return parameter

