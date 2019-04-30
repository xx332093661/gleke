# -*- encoding:utf-8 -*-
import json
import logging
import os
import threading
import traceback

import cx_Oracle

import odoo
from odoo import api
from odoo import fields
from odoo import models
from odoo.addons.his_data_synchronization.ora import Ora
# from odoo.addons.his_data_synchronization_poll.models.sync_notify import SyncNotify
from odoo.tools import config

_logger = logging.getLogger(__name__)
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'


class ProcessMessageQueueException(Exception):
    pass


class SyncProcessNotifyQueue(models.Model):
    _inherit = 'his.sync_define'


    def start_process_message_queue_thread(self):
        """开启处理通知队列线程"""
        _logger.info(u'开启处理通知消息队列线程')

        t = threading.Thread(target=self.start_process_message_queue, args=[], name='start_process_message_queue_thread')
        t.setDaemon(True)
        t.start()

    @classmethod
    def start_process_message_queue(cls):
        """数据改变通知队列处理"""
        db = odoo.sql_db.db_connect(config['db_name'])
        cr = db.cursor()

        registry = odoo.registry(config['db_name'])
        obj = registry[cls._name]

        ora_obj = Ora()

        while True:
            message = SyncNotify.notify_queue.get()
            # serial_number = getattr(message, 'serial_number')
            # _logger.info(u'正在处理消息队列，序号:%s', serial_number)

            try:
                try:
                    obj.process_message(cr, ora_obj, message)
                    cr.commit()
                except:
                    cr.rollback()
                    _logger.info(u'处理消息队列出错')
                    _logger.error(traceback.format_exc())
                    raise ProcessMessageQueueException
            except ProcessMessageQueueException:
                pass


    @classmethod
    def process_message(cls, cr, ora_obj, message):
        with api.Environment.manage():
            obj = api.Environment(cr, 1, {})[cls._name]
            obj.process_message_callback(ora_obj, message)

    @api.model
    def process_message_callback(self, ora_obj, message):
        notify_data = self.merge_message_data(message) # 合并通知的rowid

        # 插入notify_data_all
        notify_data_all = self.env['his.notify_data_all'].create({'data': json.dumps(notify_data, ensure_ascii=False, encoding='utf8', indent=4)})

        for define in self.search([], order='query_sort asc'):
            data = notify_data.get(define.name)
            if not data:
                continue

            for operation in ['insert', 'update']:
                notify_data_res = self.save_notify_data(operation, data, notify_data_all, define)
                if not notify_data_res:
                    continue

                self.process_notify_data(ora_obj, define, notify_data_res)


    @staticmethod
    def process_notify_data(ora_obj, define, notify_data):
        """处理通知数据"""

        # 查询
        if notify_data.operation == 'insert': # 插入
            query_sql = define.insert_query_sql # 查询sql
        else:
            query_sql = define.update_query_sql  # 查询sql

        if not query_sql:
            return

        row_ids = notify_data.row_ids.split(',')
        in_vars = ','.join(':%d' % i for i in xrange(len(row_ids)))

        query_result = ora_obj.query(query_sql % in_vars, args=row_ids)

        if not query_result:
            return

        # 查询回调
        getattr(define, getattr(define, notify_data.operation + '_query_callback'))(query_result)









    def save_notify_data(self, operation, notify_data, notify_data_all, define):
        """保存通知数据"""
        row_ids = notify_data.get(operation)
        if not row_ids:
            return None

        notify_data = self.env['his.notify_data'].create({
            'parent_id': notify_data_all.id,
            'sync_id': define.id,
            'operation': operation,
            'row_ids': ','.join(row_ids),
        })
        return notify_data


    @staticmethod
    def merge_message_data(message):
        """合并通知的rowid
        @return {HIS表名:{insert:[rowid0, rowid1,...], update:[rowid0, rowid1,...]}}
        """
        notify_data = {}

        for table in message.tables:
            table_name = table.name.decode('utf8').split('.')[1].lower() # "ZLHIS.病人挂号记录" 这时只要"病人挂号记录"

            if table_name not in notify_data:
                notify_data[table_name] = {}

            for row in table.rows:
                operation = row.operation
                if operation not in [cx_Oracle.OPCODE_INSERT, cx_Oracle.OPCODE_UPDATE]:
                    continue

                if operation == cx_Oracle.OPCODE_INSERT:
                    operation_name = 'insert'
                else:
                    operation_name = 'update'

                if operation_name not in notify_data[table_name]:
                    notify_data[table_name][operation_name] = []

                if row.rowid not in notify_data[table_name][operation_name]:
                    notify_data[table_name][operation_name].append(row.rowid)

        return notify_data




