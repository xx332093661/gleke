# -*- encoding:utf-8 -*-
import Queue
import json
import logging
import os
import traceback

import cx_Oracle
import time

import odoo
from odoo import api
from odoo import models
from odoo.addons.his_data_synchronization_poll.models.sync_define import SyncDefine
from odoo.addons.his_data_synchronization_poll.ora import Ora
from odoo.tools import config

_logger = logging.getLogger(__name__)
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'


class SyncEmployee(models.Model):
    _inherit = 'his.sync_define'
    his_table_name = u'人员表'
    query_queue = Queue.Queue()  # his数据改变通知队列

    def employee_base(self, result):
        """医生基础数据同步"""
        self.employee_create(result)


    def employee_insert(self, result):
        """人员插入"""
        self.employee_create(result)


    def employee_create(self, result):
        """同步人员，创建员工和用户"""

        employee_obj = self.env['hr.employee']
        users_obj = self.env['res.users']

        groups = self.env['ir.model.data'].get_object_reference('hrp_queue', 'group_hrp_doctor') # 医生组

        if isinstance(result, dict):
            result = [result]

        for res in result:
            assert isinstance(res, dict)
            if employee_obj.his_id_exist(res['his_id']): # 重复处理
                continue

            user_id = False
            if res['login']:
                user = users_obj.search([('login', '=', res['login'])])
                if not user:
                    user = users_obj.create({
                        'name': res['name'],
                        'login': res['login'],
                        'password': res['login'],
                        'active': True,
                        'share': True,
                        'email': res['login'],
                        'notify_email': 'none',
                        'groups_id': [(6, 0, [groups[1]])],
                        'tz': 'Asia/Shanghai',
                    })
                user_id = user.id
            employee_obj.create({
                'his_id': res['his_id'],
                'name': res['name'],
                'title': res['title'],
                'user_id': user_id,
                'code': res['code'], # 工号
            })


    @classmethod
    def on_employee_notify(cls, message):
        row_ids = SyncDefine.merge_notify_rowid(message, SyncEmployee.his_table_name, cx_Oracle.OPCODE_INSERT)

        if not row_ids:
            return

        db_name = config['db_name']
        db = odoo.sql_db.db_connect(db_name)
        cr = db.cursor()

        try:
            registry = odoo.registry(db_name)
            notify_data_id = registry[cls._name].employee_notify(row_ids, cr)
            cr.commit()
            SyncEmployee.query_queue.put(notify_data_id)  # 放入查询队列
        except Exception:
            cr.rollback()
            _logger.info(u'处理%s通知出错，行IDS:%s', SyncEmployee.his_table_name, row_ids)
            _logger.error(traceback.format_exc())
        finally:
            cr.close()


    @classmethod
    def employee_notify(cls, row_ids, cr):
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            notify_data_id = self.process_employee_notify(row_ids)

        return notify_data_id


    @api.model
    def process_employee_notify(self, row_ids):
        notify_data = self.env['his.notify_data'].create_notify_data(row_ids, SyncEmployee.his_table_name, 'insert') # 插入notify_data
        return notify_data.id


    @classmethod
    def start_process_query_queue_employee(cls):
        """数据改变通知队列处理"""
        db_name = config['db_name']
        db = odoo.sql_db.db_connect(db_name)
        cr = db.cursor()

        registry = odoo.registry(db_name)
        # 将未处理的通知放入队列
        try:
            registry[cls._name].get_no_process_employee_queue(cr)
        except Exception:
            cr.rollback()
            _logger.exception(u'将%s未处理的通知放入队列出错!', SyncEmployee.his_table_name)
            _logger.error(traceback.format_exc())
        finally:
            cr.close()

        while True:
            notify_data_id = SyncEmployee.query_queue.get()
            cr = db.cursor()
            try:
                registry[cls._name].process_notify_employee(notify_data_id, cr)
                cr.commit()
                time.sleep(0.5)
            except Exception:
                cr.rollback()
                _logger.error(u'处理%s通知%s出错', SyncEmployee.his_table_name, notify_data_id)
                _logger.error(traceback.format_exc())
                time.sleep(5)
                SyncEmployee.query_queue.put(notify_data_id)
            finally:
                cr.close()


    @classmethod
    def get_no_process_employee_queue(cls, cr):
        """将未处理的通知放入队列"""
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            self.no_process_employee_in_queue()


    @api.model
    def no_process_employee_in_queue(self):
        """将未处理的通知放入队列"""
        for notify_data in self.env['his.notify_data'].search([('state', '=', 'draft'), ('sync_id', '=', self.search([('name', '=', SyncEmployee.his_table_name)]).id)], order='id asc'):
            SyncEmployee.query_queue.put(notify_data.id)


    @classmethod
    def process_notify_employee(cls, notify_data_id, cr):
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            self.process_query_employee(notify_data_id)


    @api.model
    def process_query_employee(self, notify_data_id):
        ora_obj = Ora()

        notify_data = self.env['his.notify_data'].browse(notify_data_id)

        row_ids = notify_data.row_ids.split(',')
        in_vars = ','.join(':%d' % i for i in xrange(len(row_ids)))

        query_result = ora_obj.query(notify_data.sync_id.insert_query_sql % in_vars, args=row_ids)

        if query_result:
            self.employee_insert(query_result)

        notify_data.write({
            'query_result': json.dumps(query_result, ensure_ascii=False, encoding='utf8', indent=4),
            'state': 'done'
        })


