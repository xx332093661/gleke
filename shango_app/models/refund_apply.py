# -*- encoding:utf-8 -*-
from odoo import fields, models, api
from weixin_pay_interface import RefundQuery_pub
from alipay import AliPay
from alipay.compat import quote_plus, urlopen
from emqtt import Emqtt
from odoo.tools import config
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import json
import logging

_logger = logging.getLogger(__name__)


class RefundApply(models.Model):
    _name = 'his.refund_apply'
    _description = '退款申请'
    _order = 'id desc'

    partner_id = fields.Many2one('res.partner', '退款人')
    visit_partner_id = fields.Many2one('res.partner', '就诊人')

    pay_method = fields.Selection([('weixin', '微信支付'), ('alipay', '支付宝支付')], '支付方式')
    order_type = fields.Selection([('register', '挂号'), ('payment', '缴费'), ('recharge', '充值'), ('service', '便民服务')], '订单类别')
    amount_total = fields.Float('退款金额')
    trade_no = fields.Char('支付宝交易号')
    transaction_id = fields.Char('微信支付订单号')
    reason = fields.Char('退款原因')
    refund_time = fields.Datetime('退款时间')
    state = fields.Selection([('draft', '申请'), ('done', '完成')], '状态')

    alipay_ids = fields.Many2many('his.alipay_record', 'his_refund_apply_alipay_rel', 'refund_apply_id', 'alipay_id', '支付宝支付记录')
    weixin_pay_ids = fields.Many2many('his.weixin_pay_record', 'his_pay_refund_apply_weixin_rel', 'refund_apply_id', 'weixin_pay_id', '微信支付记录')
    order_ids = fields.Many2many('sale.order', 'his_refund_apply_order_rel', 'refund_apply_id', 'order_id', '订单')

    company_id = fields.Many2one('res.company', '业务医院')
    internal_id = fields.Integer('内部id')

    @api.model
    def query_refund_result(self):
        """查询退费结果"""

        # 待查询的数据
        refund_applys = self.search([('state', '=', 'draft')])
        if not refund_applys:
            return

        # 当前时间
        time_now = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        for refund_apply in refund_applys:

            company = refund_apply.company_id

            if refund_apply.pay_method == 'weixin' and refund_apply.weixin_pay_ids:
                # 微信
                weixin_pay = refund_apply.weixin_pay_ids[0]

                # 医院微信配置信息
                if not company.weixin_appid or not company.weixin_mch_id or not company.weixin_api_key:
                    continue

                refundquery = RefundQuery_pub(appid=company.weixin_appid, mch_id=company.weixin_mch_id, api_key=company.weixin_api_key)

                refundquery.setParameter('out_trade_no', weixin_pay.out_trade_no)  # 商户订单号

                # 查询微信退费结果
                result = refundquery.getResult()

                _logger.info(u'微信订单%s退费查询结果:%s' % (weixin_pay.out_trade_no, result))

                if result['return_code'] == 'SUCCESS' and result.get('result_code') == 'SUCCESS':
                    for key in result.keys():
                        if 'refund_status' in key and result[key] == 'SUCCESS':
                            # 退费成功

                            # 修改退款申请
                            refund_apply.write({
                                'state': 'done',
                                'refund_time': time_now
                            })

                            # 修改订单
                            refund_apply.order_ids.write({
                                'is_refund': True,
                                'refund_time': time_now
                            })

                            # 修改微信支付记录
                            refund_apply.weixin_pay_ids.write({
                                'is_refund': True,
                                'refund_time': time_now,
                                'refund_code': result['result_code'],
                                'refund_msg': result['return_msg'],
                            })

                            # 发送消息通知内网
                            msg = {
                                'action': 'query_refund_result',
                                'data': {
                                    'refund_apply_id': refund_apply.internal_id,
                                    'result': result
                                }
                            }

                            Emqtt.publish(refund_apply.company_id.topic, msg)

            elif refund_apply.pay_method == 'alipay' and refund_apply.alipay_ids:
                # 支付宝

                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                if base_url.endswith('/'):
                    base_url = base_url[:-1]

                # 医院微信配置信息
                if not company.alipay_app_id or not company.app_alipay_private_key or not company.app_alipay_public_key:
                    continue

                ali = AliPay(appid=company.alipay_app_id,
                             app_private_key_path=company.app_alipay_private_key_path,
                             app_alipay_public_key_path=company.app_alipay_public_key_path,
                             sign_type='RSA2',
                             app_notify_url=base_url + '/app/alipay_payback')
                # 参数
                data = {
                    "app_id": ali.appid,
                    "method": "alipay.trade.fastpay.refund.query",
                    "format": "JSON",
                    "charset": "utf-8",
                    "sign_type": ali.sign_type,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "version": "1.0",
                    "biz_content": {
                        'out_trade_no': refund_apply.alipay_ids[0].out_trade_no,
                        'out_request_no': refund_apply.alipay_ids[0].out_trade_no
                    }
                }
                # 签名
                sign = ali._sign_data_with_private_key(data, company.app_alipay_private_key_path)

                # 排序
                # ordered_items = ali.__ordered_data(data)
                complex_keys = []
                for key, value in data.items():
                    if isinstance(value, dict):
                        complex_keys.append(key)

                # 将字典类型的数据dump出来
                for key in complex_keys:
                    data[key] = json.dumps(data[key], separators=(',', ':'))

                ordered_items = sorted([(k, v) for k, v in data.items()])

                quoted_string = "&".join("{}={}".format(k, quote_plus(v)) for k, v in ordered_items)

                # 获得最终的请求字符串
                signed_string = quoted_string + "&sign=" + quote_plus(sign)

                url = "https://openapi.alipay.com/gateway.do" + "?" + signed_string

                r = urlopen(url, timeout=15)
                result = r.read().decode("utf-8")

                _logger.info(u'支付宝订单%s退费查询结果:%s' % (refund_apply.alipay_ids[0].out_trade_no, result))

                response = json.loads(result)["alipay_trade_fastpay_refund_query_response"]

                if response['code'] == '10000':
                    # 退费成功

                    # 修改退款申请
                    refund_apply.write({
                        'state': 'done',
                        'refund_time': time_now
                    })

                    # 修改订单
                    refund_apply.order_ids.write({
                        'is_refund': True,
                        'refund_time': time_now
                    })

                    # 修改支付宝支付记录
                    refund_apply.alipay_ids.write({
                        'is_refund': True,
                        'refund_time': time_now,
                        'refund_code': response['code'],
                        'refund_msg': response['msg'],
                    })

                    # 发送消息通知内网
                    msg = {
                        'action': 'query_refund_result',
                        'data': {
                             'refund_apply_id': refund_apply.internal_id,
                             'result': response
                        }
                    }

                    Emqtt.publish(refund_apply.company_id.topic, msg)




