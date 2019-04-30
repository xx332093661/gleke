# coding: utf-8
from odoo.tools import config

import logging
import json
import traceback
import paho.mqtt.client as mqtt
import time
import importlib

_logger = logging.getLogger(__name__)


class HRPMqtt():
    def __init__(self, mqtt_ip, mqtt_port, mqtt_username, mqtt_password):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.username_pw_set(mqtt_username, mqtt_password)      # 登录
        self.client.connect(mqtt_ip, port=mqtt_port, keepalive=60)  # 建立连接
        # if config.get('db_name'):
        #     db = odoo.sql_db.db_connect(config['db_name'])
        #     self.cr = db.cursor()
        #     self.pool = openerp.modules.registry.RegistryManager.get(self.cr.dbname)    # openerp7
        #     self.pool = odoo.registry(self.cr.dbname)  # odoo

    def on_connect(self, client, userdata, flags, rc):
        client.subscribe('OdooReceive', qos=0)
        client.loop_start()
        _logger.info(u'mqtt连接成功')

    def on_disconnect(self, client, userdata, rc):
        _logger.error(u'mqtt连接断开')
        while 1:
            time.sleep(10)
            try:
                client.reconnect()
                _logger.info(u'mqtt重新连接')
                break
            except Exception:
                _logger.error(traceback.format_exc())
                _logger.error(u'mqtt重连失败')

    def on_message(self, client, userdata, message):
        try:
            data = json.loads(message.payload)
            _logger.info(u'收到的mqtt消息:%s' % json.dumps(data, ensure_ascii=False, indent=True))
        except Exception:
            _logger.error(traceback.format_exc())

    def on_publish(self, client, userdata, mid):
        pass

    def publish_msg(self, topic, data):
        d = json.dumps(data, ensure_ascii=False, indent=True)
        _logger.info(u'发送到: %s 的mqtt消息:%s' % (topic, d))
        if not topic:
            _logger.error(u'发送消息失败！主题为空')
            return
        try:
            res = self.client.publish(topic, d)
        except Exception:
            _logger.error(traceback.format_exc())
            _logger.error(u'发送到消息失败！')
            return
        _logger.info(res)

# 连接内网mqtt
try:
    hrpMqtt = HRPMqtt(config['mqtt_ip'], config['mqtt_port'], config['mqtt_username'], config['mqtt_password'])
    _logger.info(u'连接mqtt服务器：%s' % config['mqtt_ip'])
    hrpMqtt.client.loop_start()
except Exception:
    hrpMqtt = None
    _logger.error(traceback.format_exc())
    _logger.info(u'连接mqtt失败')


# 发送内网消息
def send_msg(topic, msg):
    global hrpMqtt
    try:
        if hrpMqtt:
            hrpMqtt.publish_msg(topic, msg)
        else:
            hrpMqtt = HRPMqtt(config['mqtt_ip'], config['mqtt_port'], config['mqtt_username'], config['mqtt_password'])
            _logger.info(u'重连mqtt服务器：%s' % config['mqtt_ip'])
            hrpMqtt.client.loop_start()
            hrpMqtt.publish_msg(topic, msg)
    except Exception:
        _logger.error(traceback.format_exc())
        _logger.error(u'发送消息失败！')


# # 链接外网mqtt
# try:
#     hrpMqtt2 = HRPMqtt(config['mqtt_ip2'], config['mqtt_port2'], config['mqtt_username2'], config['mqtt_password2'])
#     _logger.info(u'连接mqtt服务器：%s' % config['mqtt_ip2'])
#     hrpMqtt2.client.loop_start()
# except Exception:
#     hrpMqtt2 = None
#     _logger.error(traceback.format_exc())
#     _logger.info(u'连接mqtt失败')
#
#
# # 发送外网消息
# def send_msg2(topic, msg):
#     global hrpMqtt2
#     try:
#         if hrpMqtt2:
#             hrpMqtt2.publish_msg(topic, msg)
#         else:
#             hrpMqtt2 = HRPMqtt(config['mqtt_ip2'], config['mqtt_port2'], config['mqtt_username2'], config['mqtt_password2'])
#             _logger.info(u'重连mqtt服务器：%s' % config['mqtt_ip2'])
#             hrpMqtt2.client.loop_start()
#             hrpMqtt2.publish_msg(topic, msg)
#     except Exception:
#         _logger.error(traceback.format_exc())
#         _logger.error(u'发送消息失败！')

module = {}

if not module:
    module.update({
        'emqtt': importlib.import_module('odoo.addons.his_app_hcfy.models.emqtt'),
        'config': importlib.import_module('odoo.tools.config')
    })

# module['emqtt'].Emqtt.publish(module['config'].config['extranet_topic'], payload, 2)

