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


class SyncClinicClassificationCategory(models.Model):
    _inherit = 'his.sync_define'
    his_table_name = u'诊疗分类目录'
    query_queue = Queue.Queue()  # his数据改变通知队列


    def clinic_classification_category_base(self, result):
        """基础数据同步处理"""

        clinic_classification_category_obj = self.env['his.clinic_classification_category']
        for res in result:
            if clinic_classification_category_obj.his_id_exist(res['his_id']): # 重复处理
                continue

            if res.get('id'):
                continue

            parent_id = False
            if res['parent_id']:
                parent_id = self.clinic_classification_category_recursion(clinic_classification_category_obj, result, res['parent_id'])

            self.create_clinic_classification_category(res, parent_id)


    def clinic_classification_category_insert(self, result):
        """诊疗分类目录插入"""

        clinic_classification_category_obj = self.env['his.clinic_classification_category']

        if isinstance(result, dict):
            result = [result]

        for res in result:
            assert isinstance(res, dict)
            if clinic_classification_category_obj.his_id_exist(res['his_id']): # 重复处理
                continue

            parent_id = res.pop('parent_id')
            if parent_id:
                clinic_classification_category = clinic_classification_category_obj.search([('his_id', '=', parent_id)])
                if clinic_classification_category:
                    res['parent_id'] = clinic_classification_category.id

            clinic_classification_category_obj.create(res)


    def clinic_classification_category_recursion(self, clinic_classification_category_obj, result, parent_his_id):
        """递归处理"""
        value = filter(lambda x: x['his_id'] == parent_his_id, result)[0]
        assert isinstance(value, dict)
        if value.get('id'):
            return value['id']

        parent_id = False
        if value['parent_id']:
            parent_id = self.clinic_classification_category_recursion(clinic_classification_category_obj, result, value['parent_id'])

        clinic_classification_category = self.create_clinic_classification_category(value, parent_id)
        value.update({'id': clinic_classification_category.id})
        return clinic_classification_category.id


    def create_clinic_classification_category(self, vals, parent_id):
        """创建诊疗分类目录"""
        clinic_classification_category = self.env['his.clinic_classification_category'].create({
            'his_id': vals['his_id'],
            'parent_id': parent_id,
            'name': vals['name'],
            'code': vals['code'],
        })
        return clinic_classification_category


    @classmethod
    def on_clinic_classification_category_notify(cls, message):
        row_ids = SyncDefine.merge_notify_rowid(message, SyncClinicClassificationCategory.his_table_name, cx_Oracle.OPCODE_INSERT)

        if not row_ids:
            return

        db_name = config['db_name']
        db = odoo.sql_db.db_connect(db_name)
        cr = db.cursor()

        try:
            registry = odoo.registry(db_name)
            notify_data_id = registry[cls._name].clinic_classification_category_notify(row_ids, cr)
            cr.commit()
            SyncClinicClassificationCategory.query_queue.put(notify_data_id)  # 放入查询队列
        except Exception:
            cr.rollback()
            _logger.info(u'处理%s通知出错，行IDS:%s', SyncClinicClassificationCategory.his_table_name, row_ids)
            _logger.error(traceback.format_exc())
        finally:
            cr.close()


    @classmethod
    def clinic_classification_category_notify(cls, row_ids, cr):
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            notify_data_id = self.process_clinic_classification_category_notify(row_ids)

        return notify_data_id


    @api.model
    def process_clinic_classification_category_notify(self, row_ids):
        notify_data = self.env['his.notify_data'].create_notify_data(row_ids, SyncClinicClassificationCategory.his_table_name, 'insert') # 插入notify_data
        return notify_data.id


    @classmethod
    def start_process_query_queue_clinic_classification_category(cls):
        """数据改变通知队列处理"""
        db_name = config['db_name']
        db = odoo.sql_db.db_connect(db_name)
        cr = db.cursor()

        registry = odoo.registry(db_name)
        # 将未处理的通知放入队列
        try:
            registry[cls._name].get_no_process_clinic_classification_category_queue(cr)
        except Exception:
            cr.rollback()
            _logger.exception(u'将%s未处理的通知放入队列出错!', SyncClinicClassificationCategory.his_table_name)
            _logger.error(traceback.format_exc())
        finally:
            cr.close()

        while True:
            notify_data_id = SyncClinicClassificationCategory.query_queue.get()
            cr = db.cursor()
            try:
                registry[cls._name].process_notify_clinic_classification_category(notify_data_id, cr)
                cr.commit()
                time.sleep(0.5)
            except Exception:
                cr.rollback()
                _logger.error(u'处理%s通知%s出错', SyncClinicClassificationCategory.his_table_name, notify_data_id)
                _logger.error(traceback.format_exc())
                time.sleep(5)
                SyncClinicClassificationCategory.query_queue.put(notify_data_id)
            finally:
                cr.close()


    @classmethod
    def get_no_process_clinic_classification_category_queue(cls, cr):
        """将未处理的通知放入队列"""
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            self.no_process_clinic_classification_category_in_queue()


    @api.model
    def no_process_clinic_classification_category_in_queue(self):
        """将未处理的通知放入队列"""
        for notify_data in self.env['his.notify_data'].search([('state', '=', 'draft'), ('sync_id', '=', self.search([('name', '=', SyncClinicClassificationCategory.his_table_name)]).id)], order='id asc'):
            SyncClinicClassificationCategory.query_queue.put(notify_data.id)


    @classmethod
    def process_notify_clinic_classification_category(cls, notify_data_id, cr):
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            self.process_query_clinic_classification_category(notify_data_id)


    @api.model
    def process_query_clinic_classification_category(self, notify_data_id):
        ora_obj = Ora()

        notify_data = self.env['his.notify_data'].browse(notify_data_id)

        row_ids = notify_data.row_ids.split(',')
        in_vars = ','.join(':%d' % i for i in xrange(len(row_ids)))

        query_result = ora_obj.query(notify_data.sync_id.insert_query_sql % in_vars, args=row_ids)

        if query_result:
            self.clinic_classification_category_insert(query_result)

        notify_data.write({
            'query_result': json.dumps(query_result, ensure_ascii=False, encoding='utf8', indent=4),
            'state': 'done'
        })



