# coding:utf-8

import base64
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA

import logging

_logger = logging.getLogger(__name__)


class AlipayInterface(object):

    def __init__(self, app_id, pri_key, pub_key):
        self.app_id = app_id
        # self.pri_key = '-----BEGIN RSA PRIVATE KEY-----\n' + pri_key + '\n-----END RSA PRIVATE KEY-----'
        # self.pub_key = '-----BEGIN PUBLIC KEY-----\n' + pub_key + '\n-----BEGIN PUBLIC KEY-----'
        self.charset = 'utf-8'
        self.method = 'alipay.trade.app.pay'
        self.notify_url = '/app/alipay_payback'
        self.sign_type = 'RSA'
        self.version = '1.0'

    def build_sign_data(self, base_url, biz_content, time_now_str):
        url = 'app_id=%s' % self.app_id
        url += '&biz_content=%s' % biz_content
        url += '&charset=%s' % self.charset
        url += '&method=%s' % self.method
        url += '&notify_url=%s' % (base_url + self.notify_url)
        url += '&sign_type=%s' % self.sign_type
        url += '&timestamp=%s' % time_now_str
        url += '&version=%s' % self.version
        _logger.info(u'待签名字符串:%s', url)
        return url

    def sign(self, data):
        key = RSA.importKey(self.pri_key)
        h = SHA.new(data)
        signer = PKCS1_v1_5.new(key)
        signature = signer.sign(h)
        return base64.b64encode(signature)

    def verify(self, data, signature):
        key = RSA.importKey(self.pub_key)
        h = SHA.new(data)
        verifier = PKCS1_v1_5.new(key)
        if verifier.verify(h, base64.b64decode(signature)):
            return True
        return False
