# -*- encoding:utf-8 -*-
import importlib
import json
import logging
import traceback
import paho.mqtt.client as mqtt
import uuid

import odoo
from odoo import api, models
from odoo.tools import config

_logger = logging.getLogger(__name__)
EmqttMessageProcess = {}


class Emqtt(models.TransientModel):
    _name = 'shango.emqtt'

    connect_return_code = {0: u'0-连接成功', 1: u'1-不正确的协议版本', 2: u'2-无效的客户端标识符', 3: u'3-服务器不可用', 4: u'4-用户名或密码错误', 5: u'5-未授权'}
    client_setup_up = False  # 客户端是否启动

    topic = config['topic'] # 外网

    client = mqtt.Client(client_id=topic, clean_session=False) # clean_session 存储因客户商离线而错过的消息, client_id: 当clean_session为False必填且不能重复
    client.on_connect = lambda client, userdata, flags, rc: Emqtt.on_connect(client, rc)
    client.on_message = lambda client, userdata, message: Emqtt.on_message(message)
    client.on_publish = lambda client, userdata, mid: Emqtt.on_publish(mid)
    client.on_disconnect = lambda client, userdata, rc: Emqtt.on_disconnect(client)
    client.on_subscribe = lambda client, userdata, mid, granted_qos: Emqtt.on_subscribe(mid, granted_qos)


    @classmethod
    def on_connect(cls, client, rc):
        """
        @param client:
        @param rc: return code 0-连接成功 1-不正确的协议版本 2-无效的客户端标识符 3-服务器不可用 4-用户名或密码错误 5-未授权
        @return:
        """
        _logger.info(u'Emqtt连接:%s!', cls.connect_return_code[rc])
        if rc == 0:
            client.subscribe(cls.topic, qos=0) # internet 外网  intranet 内网


    @staticmethod
    def on_disconnect(client):
        _logger.info(u'Emqtt断开连接!')
        client.reconnect()


    @staticmethod
    def on_subscribe(mid, granted_qos):
        _logger.info(u'订阅%s成功, %s, %s', Emqtt.topic, mid, granted_qos)


    @classmethod
    def publish(cls, target_topic, payload, qos=2):
        payload.update({
            'source_topic': Emqtt.topic,
            'identifier': str(uuid.uuid1()),
            'mac': '',
            'token': ''
        })

        (result, mid) = cls.client.publish(target_topic, json.dumps(payload), qos=qos)

        _logger.info(u'Emqtt发送数据:%s, %s', target_topic, json.dumps(payload, ensure_ascii=False, encoding='utf8'))
        _logger.info(u'Emqtt发送数据状态(result:%s, mid: %s)', result, mid)

        # 保存到数据库
        db_name = config['db_name']
        db = odoo.sql_db.db_connect(db_name)
        cr = db.cursor()
        try:
            registry = odoo.registry(db_name)
            with api.Environment.manage():
                self = api.Environment(cr, 1, {})[registry[cls._name]._name]
                self.env['his.base_data_message'].create({
                    'payload': json.dumps(payload['data'], ensure_ascii=False, encoding='utf8', indent=4),
                    'action': payload['action'],
                    'state': 'done',
                    'source_topic': Emqtt.topic,
                    'accept_topic': target_topic,
                    'identifier': payload['identifier'],
                    'msg_type': 'send',
                    'mac': payload['mac'],
                    'token': payload['token'],
                })

            cr.commit()
        except Exception:
            cr.rollback()
            _logger.error(traceback.format_exc())
        finally:
            cr.close()


    @staticmethod
    def on_publish(mid):
        _logger.info(u'Emqtt消息发布成功:%s', mid)


    @classmethod
    def on_message(cls, message):
        try:
            data = json.loads(message.payload)
            _logger.info(u'Emqtt收到的数据:%s', json.dumps(data, ensure_ascii=False, encoding='utf8'))
        except ValueError:
            _logger.error(u'解析数据:%s发生错误', message.payload)
            return

        db_name = config['db_name']
        db = odoo.sql_db.db_connect(db_name)
        cr = db.cursor()
        try:
            registry = odoo.registry(db_name)
            message = registry[cls._name].process_message(cr, data)
            cr.commit()

            # 将消息放入队列
            if message:
                if not EmqttMessageProcess.get('emqtt'):
                    EmqttMessageProcess['emqtt'] = importlib.import_module('odoo.addons.shango_app.models.emqtt_message_process')

                EmqttMessageProcess['emqtt'].EmqttMessageProcess.base_data_queue.put(message.id)
        except:
            cr.rollback()
            _logger.error(u'处理数据:%s发生错误!', data)
            _logger.error(traceback.format_exc())
        finally:
            cr.close()


    @classmethod
    def process_message(cls, cr, data):
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            return self.process_message_callback(data)


    @api.model
    def process_message_callback(self, data):
        # m_base_data_msg = self.env['his.base_data_message']
        try:
            # 验证合法性
            mac = data['mac']
            token = data['token']
            source_topic = data['source_topic']
            identifier = data['identifier']

            # 内网传递的消息不验证合法性
            intranet_topic = [company.topic for company in self.env['res.company'].search([('id', '!=', 1)]) if company.topic]
            if source_topic not in intranet_topic:
                app_token = self.env['his.app_token'].search([('mac', '=', mac)], order='id desc', limit=1)
                if not app_token:
                    _logger.error(u'消息(source_topic:%s, identifier:%s, mac:%s)没有对应的令牌!', source_topic, identifier, mac)
                    return

                if app_token.token != token:
                    _logger.error(u'消息(source_topic:%s, identifier:%s, mac:%s)令牌%s错误，正确令牌:%s!', source_topic, identifier, mac, token, app_token.token)
                    return

            base_data_message_obj = self.env['his.base_data_message']
            # 避免重复处理
            if base_data_message_obj.search([('source_topic', '=', source_topic), ('identifier', '=', identifier)]):
                _logger.info(u'消息(source_topic:%s, identifier:%s)重复发送，丢弃', source_topic, identifier)
                return

            message = base_data_message_obj.create({
                'payload': json.dumps(data['data'], ensure_ascii=False, encoding='utf8', indent=4),
                'action': data['action'],
                'source_topic': source_topic,
                'accept_topic': Emqtt.topic,
                'identifier': identifier,
                'msg_type': 'accept',
                'mac': data['mac'],
                'token': data['token'],
            })
            return message
        except:
            _logger.error(u"Emqtt处理消息发生错误，消息:%s", data)
            _logger.error(traceback.format_exc())


    @classmethod
    def start_up_emqtt_client(cls):
        """启动Emqtt客户端"""
        if cls.client_setup_up:
            return

        cls.client_setup_up = True
        cls.client.username_pw_set(config['emqtt_user'], config['emqtt_pwd'])  # 登录
        cls.client.connect(config['emqtt_host'], port=config['emqtt_port'], keepalive=60)  # 建立连接
        cls.client.loop_start()


# 启动Emqtt连接
Emqtt.start_up_emqtt_client()








