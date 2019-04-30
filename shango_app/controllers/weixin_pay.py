# -*- coding: utf-8 -*-
from collections import OrderedDict
import hashlib
import json
import logging
import random
import string
import urllib
from urllib import quote
import urllib2
import time
from xmltodict import parse, unparse
from openerp.http import request
from openerp.tools import float_round, config
from openerp.addons.hrp_common import WxUnifiedorderError

_logger = logging.getLogger(__name__)


class WeiXin(object):
    """微信支付,公众号基类"""
    appid = "" # APPID
    mch_id = "" # 商户号
    key = "" # API密钥

    trade_type = "" # 交易类型

    _notify_url = '' # 通知地址
    unifiedorder_url = 'https://api.mch.weixin.qq.com/pay/unifiedorder' # 统一下单接口地址

    error_message = {
        'NOAUTH': '商户未开通此接口权限',
        'NOTENOUGH': '用户帐号余额不足',
        'ORDERPAID': '商户订单已支付，无需重复操作',
        'ORDERCLOSED': '当前订单已关闭，无法支付',
        'SYSTEMERROR': '系统超时',
        'APPID_NOT_EXIST': '参数中缺少APPID',
        'MCHID_NOT_EXIST': '参数中缺少MCHID',
        'APPID_MCHID_NOT_MATCH': 'appid和mch_id不匹配',
        'LACK_PARAMS': '缺少必要的请求参数',
        'OUT_TRADE_NO_USED': '同一笔交易不能多次提交',
        'SIGNERROR': '参数签名结果不正确',
        'XML_FORMAT_ERROR': 'XML格式错误',
        'REQUIRE_POST_METHOD': '未使用post传递参数',
        'POST_DATA_EMPTY': 'post数据不能为空',
        'NOT_UTF8': '未使用指定编码格式',
    }

    def __init__(self, acquirer, order_id):
        # 订单
        order = request.env['sale.order'].with_env(request.env(user=1)).browse(order_id)
        # 总金额
        if acquirer.environment == 'test':
            total_fee = 1
        else:
            acquirer = request.env['ir.model.data'].get_object('hrp_payment_balance', 'payment_acquirer_balance')
            transaction = request.env['payment.transaction'].search(
                [('acquirer_id', '=', acquirer.id), ('sale_order_id', '=', order_id)])
            if transaction:
                amount = transaction.amount
                total_fee = str(int(float_round(order.amount_total - amount, 2) * 100))
            else:
                total_fee = str(int(float_round(order.amount_total, 2) * 100))

        # self.body = order.order_line[0].product_id.name  # 商品描述
        self.body = u'订购%s日%s' % (order.validity_date, order.meal_categ_id.name,)  # 订单详情
        self.order = order

        self.out_trade_no = order.name  # 商户网站唯一订单号
        self.total_fee = str(total_fee)  # 总金额
        self.spbill_create_ip = request.httprequest.remote_addr # 终端IP
        # self.spbill_create_ip = '121.201.14.17' # 终端IP

        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        if base_url.endswith('/'):
            base_url = base_url[:-1]

        self.notify_url = base_url + self._notify_url

    @staticmethod
    def create_sign(data, app_key=None, sign_type='md5'):
        """创建签名"""
        # 过滤空值参数
        od = {key: val for key, val in data.items() if val}
        # 按键排序
        od = OrderedDict(sorted(od.items(), key=lambda t: t[0]))
        # 待签名字符串
        sign_str = '&'.join(['='.join([key, val if isinstance(val, basestring) else str(val)]) for key, val in od.items()]) + ('&key=' + app_key if app_key else '')
        # _logger.info(u'微信支付签名字符串:%s',  sign_str)
        # 签名
        if sign_type == 'md5':
            sign = hashlib.md5(sign_str.encode('utf8')).hexdigest().upper()
        else:
            sign = hashlib.sha1(sign_str.encode('utf8')).hexdigest().upper()
        # _logger.info(u'微信支付签名结果:%s', sign)
        return sign

    @staticmethod
    def build_nonce_str():
        """生成一个随机字符串"""
        return ''.join(random.sample(string.ascii_letters + string.digits, random.randint(8, 32)))

    @staticmethod
    def create_timestamp():
        """时间"""
        return int(time.time())

    @staticmethod
    def verify_sign(data, key):
        """校验签名 按照字母顺序排序，然后使用阿里云的公匙验证。"""
        wx_sign = data.pop('sign')
        # 签名
        sign = WeiXin.create_sign(data, key)

        return wx_sign == sign

    @staticmethod
    def verify_status_fail():
        """签名失败返回数据"""
        message = {
            'return_code': 'FAIL',
            'return_msg': u'签名验证失败',
        }
        message = unparse({'xml': message}, full_document=False)
        return message

    @staticmethod
    def verify_status_success():
        """签名成功返回数据"""
        return unparse({'xml': {'return_code': 'SUCCESS', 'return_msg': 'OK'}}, full_document=False)

    def unifiedorder(self, openid=None, device_info=None):
        """统一下单"""
        parameters = {
            'appid': self.appid, # 公众账号ID
            'mch_id': self.mch_id, # 商户号
            'nonce_str': self.build_nonce_str(),  # 随机字符串
            'body': self.body, # 商品描述
            'out_trade_no': self.out_trade_no, # 商户订单号
            'total_fee': self.total_fee, # 总金额
            'spbill_create_ip': self.spbill_create_ip, # 终端IP
            'notify_url': self.notify_url, # 通知地址
            'trade_type': self.trade_type, # 交易类型
        }

        if openid:
            parameters.update({'openid': openid})
        if device_info:
            parameters.update({'device_info': device_info})
        # _logger.info(parameters)
        # 签名
        sign = self.create_sign(parameters, self.key)
        parameters.update({'sign': sign})
        # _logger.info(parameters)

        _logger.info(u'调用微信统一下单接口我传递的数据:%s', json.dumps(parameters, ensure_ascii=False, encoding='utf8'))

        # 转换成xml字符串
        paras = unparse({'xml': parameters}, pretty=True, full_document=False)
        paras = paras.encode('utf-8')
        # 提交,得到预支付ID
        content = urllib2.urlopen(self.unifiedorder_url, paras).read()

        # 解析响应
        response = parse(content)['xml']

        _logger.info(u'调用微信统一下单接口返回数据:%s', json.dumps(response, ensure_ascii=False, encoding='utf8'))


        if response['return_code'] == 'FAIL':
            raise WxUnifiedorderError(response['return_msg'])

        if response['result_code'] == 'FAIL':
            err_code = response['err_code']
            message = self.error_message.get(err_code, u'调用统一下单接口发生错误!')
            raise WxUnifiedorderError(message)

        # 预支付ID
        prepay_id = response['prepay_id']
        return prepay_id


class WXApp(WeiXin):
    """APP支付"""
    appid = config['wx_open_appid'] # 公众账号ID
    mch_id = config['wx_open_mchid'] # 商户号
    key = config['wx_open_key'] # API密钥

    trade_type = 'APP' # 交易类型
    package = 'Sign=WXPay' # 扩展字段, 暂填写固定值Sign=WXPay

    _notify_url = '/app/wx/app/notify' # 通知地址

    def build_pay_data(self):
        """构建支付数据"""
        # 统一下单,得到预支付ID
        prepay_id = self.unifiedorder()
        parameters = {
            'appid': self.appid, # 公众账号ID
            'partnerid': self.mch_id, # 商户号
            'prepayid': prepay_id, # 预支付交易会话ID
            'package': self.package, # 扩展字段, 暂填写固定值Sign=WXPay
            'noncestr': self.build_nonce_str(), # 随机字符串
            'timestamp': str(self.create_timestamp()), # 时间戳
        }
        # 签名
        sign = self.create_sign(parameters, self.key)
        parameters.update({'sign': sign})

        return parameters


class WXServer(WeiXin):
    """公众号"""
    appid = config['wx_server_appid'] # 公众账号ID
    mch_id = config['wx_server_mchid'] # 商户号
    key = config['wx_server_key'] # API密钥

    trade_type = 'JSAPI' # 交易类型

    appsecret = config['wx_server_secret']

    sign_type = 'MD5' # 签名方式

    _notify_url = '/app/wx/server/notify' # 通知地址

    # 网页授权路径
    oauth_url = 'https://open.weixin.qq.com/connect/oauth2/authorize'
    get_oauth_access_token_url = 'https://api.weixin.qq.com/sns/oauth2/access_token'
    get_openid_redirect_uri = '/app/wx/get_openid_cb'


    @staticmethod
    def get_user_openid_code_url(uid, url):
        """获取openid"""
        # 是否是微信
        user_agent = request.httprequest.environ['HTTP_USER_AGENT']
        if user_agent.find('MicroMessenger') == -1:
            return

        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        if base_url.endswith('/'):
            base_url = base_url[:-1]

        redirect_uri = base_url + WXServer.get_openid_redirect_uri

        # _logger.info(11111111111111)
        # _logger.info(url)
        if not url:
            url = u''

        url = '?url=%s' % quote(url)

        redirect_uri += url

        paras = {
            'appid': WXServer.appid,  # 调用接口凭证
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'snsapi_base',
            'state': str(uid)
        }
        # https://open.weixin.qq.com/connect/oauth2/authorize?appid=xxx&redirect_uri=http://www.toncen.net/app/wx/get_openid_cb?to=xxx&toParams=xxx&response_type=code&scope=snsapi_base&state=123#wechat_redirect
        url = WXServer.oauth_url + "?" + urllib.urlencode(paras) + '#wechat_redirect'
        return url

    @staticmethod
    def get_openid_callback(code):
        """得到openid回调"""
        paras = {
            'appid': WXServer.appid,
            'secret': WXServer.appsecret,  # 普通用户的标识，对当前公众号唯一
            'code': code,
            'grant_type': 'authorization_code'
        }
        url = WXServer.get_oauth_access_token_url + "?" + urllib.urlencode(paras)
        response = urllib2.urlopen(url)
        data = response.read()
        response.close()
        data = json.loads(data)
        openid = data['openid']
        return openid

    def build_pay_data(self):
        """构建支付数据"""
        # 统一下单,得到预支付ID
        openid = self.order.partner_id.openid
        device_info = 'WEB'
        prepay_id = self.unifiedorder(openid, device_info)
        parameters = {
            'appId': self.appid, # 公众账号ID
            'timeStamp': self.create_timestamp(), # 时间戳
            'nonceStr': self.build_nonce_str(), # 随机字符串
            'package': 'prepay_id=%s' % prepay_id, # 扩展字段, 暂填写固定值Sign=WXPay
            'signType': self.sign_type, # 签名方式
        }
        # 签名
        sign = self.create_sign(parameters, self.key)

        parameters.update({'paySign': sign})
        _logger.info(u'公众号支付支付数据:%s', parameters)
        return parameters

    @staticmethod
    def build_jsapi_config():
        """在微信公众号中调用jsapi"""
        noncestr = WeiXin.build_nonce_str()
        jsapi_ticket = request.env['hrp.jsapi_ticket'].get_jsapi_ticket()
        timestamp = WeiXin.create_timestamp()

        message = {
            'noncestr': noncestr, # 随机字符串
            'jsapi_ticket': jsapi_ticket, # 有效的jsapi_ticket
            'timestamp': timestamp, #
            'url': 'http://www.toncen.net/wx/index', # 当前网页的URL，不包含#及其后面部分
        }
        # 签名
        sign = WeiXin.create_sign(message, sign_type='sha1')

        return {
            'debug': False, # 开启调试模式,调用的所有api的返回值会在客户端alert出来，若要查看传入的参数，可以在pc端打开，参数信息会通过log打出，仅在pc端时才会打印
            'appId': WXServer.appid,
            'timestamp': timestamp,
            'nonceStr': noncestr,
            'signature': sign,
            'jsApiList': []
        }


class WXShaoMa(WXServer):
    """扫码支付"""
    trade_type = 'NATIVE' # 交易类型

    qr_url = 'weixin：//wxpay/bizpayurl?'

    @staticmethod
    def build_qr_data(product_id, width=300, height=300):
        """生成二维码的数据"""
        parameters = {
            'appid': WXShaoMa.appid, # 公众账号ID
            'mch_id': WXShaoMa.mch_id, # 商户号
            'time_stamp': str(int(time.time())), # 时间戳
            'nonce_str': WeiXin.build_nonce_str(), # 随机字符串
            'product_id': product_id, # 扩展字段, 暂填写固定值Sign=WXPay
        }
        # 签名
        sign = WeiXin.create_sign(parameters)
        parameters.update({'sign': sign})

        val = WXShaoMa.qr_url + '&'.join(['='.join([key, str(val) if not isinstance(val, basestring) else val]) for key, val in parameters.items()])
        return '/app/barcode/?my_type=%s&value=%s&width=%s&height=%s' % ('QR', val, width, height)

    @staticmethod
    def shao_ma_callback(return_code='SUCCESS', return_msg=u'', prepay_id='', result_code='SUCCESS', err_code_des=u'', data=None):
        """"""
        if not data:
            data = {}

        message = {
            'return_code': return_code, # SUCCESS/FAIL,此字段是通信标识，非交易标识，交易是否成功需要查看result_code来判断
            'return_msg': return_msg, # 返回信息，如非空，为错误原因;签名失败;具体某个参数格式校验错误.
            'appid': WXShaoMa.appid, # 公众账号ID
            'mch_id': WXShaoMa.mch_id, # 商户号
            'nonce_str': WeiXin.build_nonce_str(), # 随机字符串
            'prepay_id': prepay_id, # 预支付ID
            'result_code': result_code, # 业务结果 SUCCESS/FAIL
            'err_code_des': err_code_des, # 错误描述 当result_code为FAIL时，商户展示给用户的错误提
        }

        message.update(data)

        # 签名
        sign = WeiXin.create_sign(message)

        message.update({'sign': sign})
        message = unparse({'xml': message}, full_document=False)
        return message

    @staticmethod
    def verify_status_fail_shao_ma():
        """签名失败返回数据"""
        message = WXShaoMa.shao_ma_callback(return_msg=u'签名验证失败', result_code='FAIL', err_code_des=u'验证签名发生错误')
        return message

    @staticmethod
    def pay_timeout():
        """订单支付超时"""
        message = WXShaoMa.shao_ma_callback(result_code='FAIL', err_code_des=u'订单支付超时')
        return message

    @staticmethod
    def call_unifiedorder_error(err_code_des=None):
        """调用统一下单接口发生错误"""
        if not err_code_des:
            err_code_des = u'调用统一下单接口发生错误'

        message = WXShaoMa.shao_ma_callback(result_code='FAIL', err_code_des=err_code_des)
        return message

    def build_pay_data(self):
        """构建支付数据"""

        # 统一下单,得到预支付ID
        prepay_id = self.unifiedorder()

        message = WXShaoMa.shao_ma_callback(prepay_id=prepay_id)
        return message


