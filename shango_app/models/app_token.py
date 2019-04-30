# -*- coding: utf-8 -*-
import uuid
import logging

from odoo import models, fields
from ..models.emqtt import Emqtt

_logger = logging.getLogger(__name__)


class AppToken(models.Model):
    _name = 'his.app_token'
    _description = 'APP令牌'

    mac = fields.Char('mac地址')
    token = fields.Char('令牌')


    def create_token(self, mac):
        """生成令牌"""
        token = str(uuid.uuid1())
        self.create({
            'mac': mac,
            'token': token,
        })

        # 发送消息通知内网医院
        msg = {
            'action': 'app_start',
            'data': {
                'mac': mac,
                'token': token,
            }
        }
        Emqtt.publish('public', msg)
        return token


    def validate_token(self, mac, token):
        """验证令牌"""
        app_token = self.search([('mac', '=', mac)], order='id desc', limit=1)
        if not app_token:
            _logger.error(u'mac:%s没有对应的令牌!', mac)
            return

        if app_token.token != token:
            _logger.error(u'mac:%s令牌%s错误，正确令牌:%s!', mac, token, app_token.token)
            return

        return True

