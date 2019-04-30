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


class SyncProductPrice(models.Model):
    _inherit = 'his.sync_define'
    his_table_name = u'收费价目'
    query_queue = Queue.Queue()  # his数据改变通知队列


    def product_price_update(self, result):
        product_obj = self.env['product.template'].sudo()
        for res in result:
            product = product_obj.search([('his_id', '=', res['his_id'])])
            if not product:
                continue

            if product.list_price != res['list_price']:
                product.list_price = res['list_price']


    @classmethod
    def on_product_price_notify(cls, message):
        row_ids = SyncDefine.merge_notify_rowid(message, SyncProductPrice.his_table_name, cx_Oracle.OPCODE_INSERT)

        if not row_ids:
            return

        db_name = config['db_name']
        db = odoo.sql_db.db_connect(db_name)
        cr = db.cursor()

        try:
            registry = odoo.registry(db_name)
            notify_data_id = registry[cls._name].product_price_notify(row_ids, cr)
            cr.commit()
            SyncProductPrice.query_queue.put(notify_data_id)  # 放入查询队列
        except Exception:
            cr.rollback()
            _logger.info(u'处理%s通知出错，行IDS:%s', SyncProductPrice.his_table_name, row_ids)
            _logger.error(traceback.format_exc())
        finally:
            cr.close()


    @classmethod
    def product_price_notify(cls, row_ids, cr):
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            notify_data_id = self.process_product_price_notify(row_ids)

        return notify_data_id


    @api.model
    def process_product_price_notify(self, row_ids):
        notify_data = self.env['his.notify_data'].create_notify_data(row_ids, SyncProductPrice.his_table_name, 'update') # 插入notify_data
        return notify_data.id


    @classmethod
    def start_process_query_queue_product_price(cls):
        """数据改变通知队列处理"""
        db_name = config['db_name']
        db = odoo.sql_db.db_connect(db_name)
        cr = db.cursor()

        registry = odoo.registry(db_name)
        # 将未处理的通知放入队列
        try:
            registry[cls._name].get_no_process_product_price_queue(cr)
        except Exception:
            cr.rollback()
            _logger.exception(u'将%s未处理的通知放入队列出错!', SyncProductPrice.his_table_name)
            _logger.error(traceback.format_exc())
        finally:
            cr.close()

        while True:
            notify_data_id = SyncProductPrice.query_queue.get()
            cr = db.cursor()
            try:
                registry[cls._name].process_notify_product_price(notify_data_id, cr)
                cr.commit()
                time.sleep(0.5)
            except Exception:
                cr.rollback()
                _logger.error(u'处理%s通知%s出错', SyncProductPrice.his_table_name, notify_data_id)
                _logger.error(traceback.format_exc())
                time.sleep(5)
                SyncProductPrice.query_queue.put(notify_data_id)
            finally:
                cr.close()


    @classmethod
    def get_no_process_product_price_queue(cls, cr):
        """将未处理的通知放入队列"""
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            self.no_process_product_price_in_queue()


    @api.model
    def no_process_product_price_in_queue(self):
        """将未处理的通知放入队列"""
        for notify_data in self.env['his.notify_data'].search([('state', '=', 'draft'), ('sync_id', '=', self.search([('name', '=', SyncProductPrice.his_table_name)]).id)], order='id asc'):
            SyncProductPrice.query_queue.put(notify_data.id)


    @classmethod
    def process_notify_product_price(cls, notify_data_id, cr):
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            self.process_query_product_price(notify_data_id)


    @api.model
    def process_query_product_price(self, notify_data_id):
        ora_obj = Ora()

        notify_data = self.env['his.notify_data'].browse(notify_data_id)

        row_ids = notify_data.row_ids.split(',')
        in_vars = ','.join(':%d' % i for i in xrange(len(row_ids)))

        query_result = ora_obj.query(notify_data.sync_id.update_query_sql % in_vars, args=row_ids)

        if query_result:
            self.product_price_update(query_result)

        notify_data.write({
            'query_result': json.dumps(query_result, ensure_ascii=False, encoding='utf8', indent=4),
            'state': 'done'
        })


