# -*- encoding:utf-8 -*-
import json
import uuid
import time

import paho.mqtt.client as mqtt


config = {
    'topic': 'dddd',
    'mqtt_username_extranet': 'admin',
    'mqtt_password_extranet': 'shangoadmin',
    'mqtt_ip_extranet': '192.168.0.130',
    'mqtt_port_extranet': 1883
}



class Emqtt(object):

    connect_return_code = {0: u'0-连接成功', 1: u'1-不正确的协议版本', 2: u'2-无效的客户端标识符', 3: u'3-服务器不可用', 4: u'4-用户名或密码错误', 5: u'5-未授权'}
    client_setup_up = False  # 客户端是否启动

    topic = config['topic'] # 内网

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
        print 'on_connect'


    @staticmethod
    def on_disconnect(client):
        print 'on_disconnect'


    @staticmethod
    def on_subscribe(mid, granted_qos):
        pass


    @classmethod
    def publish(cls, target_topic, payload, qos=0):
        payload.update({
            'source_topic': 'hcfy',
            'identifier': str(uuid.uuid1()),
            'mac': '',
            'token': ''
        })

        cls.client.publish(target_topic, json.dumps(payload), qos=qos)


    @staticmethod
    def on_publish(mid):
        print u'Emqtt消息发布成功:', mid


    @classmethod
    def on_message(cls, message):
        pass




    @classmethod
    def start_up_emqtt_client(cls):
        """启动Emqtt客户端"""
        if cls.client_setup_up:
            return

        cls.client_setup_up = True
        cls.client.username_pw_set(config['mqtt_username_extranet'], config['mqtt_password_extranet'])  # 登录
        cls.client.connect(config['mqtt_ip_extranet'], port=config['mqtt_port_extranet'], keepalive=60)  # 建立连接
        cls.client.loop_start()


# 启动Emqtt连接
Emqtt.start_up_emqtt_client()
data = {

    'action': 'add_patient',
    'data': {
        'partner_id': 15,
        'internal_id': 1,
        'company_topic': 'hcfy'
    }
}
Emqtt.publish('extranet', data, qos=2)
time.sleep(2)









