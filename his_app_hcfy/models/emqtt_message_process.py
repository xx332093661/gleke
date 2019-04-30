# -*- encoding:utf-8 -*-
import Queue
import json
import logging
import threading
import traceback
from functools import wraps



import odoo
from odoo import api
from odoo import models
from odoo.tools import config

_logger = logging.getLogger(__name__)


def emqtt_wraps(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        _logger.info(u'%s收到数据:%s', func.func_name, json.dumps(kwargs, ensure_ascii=False, encoding='utf8', indent=None))
        return func(self, *args, **kwargs)
    return wrapper


class EmqttMessageProcess(models.TransientModel):
    """Emqtt消息处理"""
    _inherit = 'his.emqtt'
    base_data_queue = Queue.Queue()  # 基础数据队列
    process_base_data_thread_started = False  # 是否已开启处理基础数据线程

    @api.model
    def ir_cron_start_process_base_data_thread(self):
        """开启处理基础数据线程"""
        if EmqttMessageProcess.process_base_data_thread_started: # 是否已开启处理基础数据线程
            return True

        EmqttMessageProcess.process_base_data_thread_started = True
        self.start_process_base_data_thread() # 处理通知消息队列


    def start_process_base_data_thread(self):
        """处理基础数据线程"""
        t = threading.Thread(target=self.start_process_base_data, args=[], name='process_base_data_thread')
        t.setDaemon(True)
        t.start()


    @classmethod
    def start_process_base_data(cls):
        """处理基础数据"""
        db_name = config['db_name']
        db = odoo.sql_db.db_connect(db_name)
        cr = db.cursor()

        registry = odoo.registry(db_name)
        # 将未处理的基础数据放入队列
        try:
            registry[cls._name].no_processed_in_queue(cr)
            cr.commit()
        except Exception:
            cr.rollback()
            _logger.exception(u'将未处理的基础数据放入队列出错!')
            _logger.error(traceback.format_exc())
        finally:
            cr.close()

        while True:
            message_id = EmqttMessageProcess.base_data_queue.get()
            cr = db.cursor()
            try:
                result = registry[cls._name].process_base_data(message_id, cr)
                if result:
                    cls.publish(result[0], result[1])
                cr.commit()
            except Exception:
                cr.rollback()
                _logger.error(u'处理基础数据%s出错', message_id)
                _logger.error(traceback.format_exc())
                # EmqttMessageProcess.base_data_queue.put(message_id)
            finally:
                cr.close()


    @classmethod
    def no_processed_in_queue(cls, cr):
        """将未处理的基础数据放入队列"""
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            self.no_processed_in_queue_callback()


    @api.model
    def no_processed_in_queue_callback(self):
        """将未处理的基础数据放入队列"""
        for message in self.env['his.base_data_message'].search([('state', '=', 'draft'), ('refund_apply_id', '=', False)], order='id asc'):
            EmqttMessageProcess.base_data_queue.put(message.id)


    @classmethod
    def process_base_data(cls, message_id, cr):
        """处理基础数据"""
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            return self.process_base_data_callback(message_id)


    @api.model
    def process_base_data_callback(self, message_id):
        """处理基础数据"""

        message = self.env['his.base_data_message'].browse(message_id)
        action = message.action
        if hasattr(self, action):
            result = getattr(self, action)(message)
            message.state = 'done'
            return result
        else:
            _logger.error(u"Emqtt处理消息发生错误，方法%s不存在", action)




















