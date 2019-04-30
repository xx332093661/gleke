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


class SyncProduct(models.Model):
    _inherit = 'his.sync_define'
    his_table_name = u'收费项目目录'
    query_queue = Queue.Queue()  # his数据改变通知队列

    def product_base(self, result):
        self.product_template(result)


    def product_template(self, result):
        product_template_obj = self.env['product.template']
        category_obj = self.env['product.category']
        uom_categ_obj = self.env['product.uom.categ']
        uom_obj = self.env['product.uom']
        for res in result:
            # 重复处理
            if product_template_obj.his_id_exist(res['his_id']):
                continue

            # 创建目录
            category = category_obj.search([('name', '=', res['categ_name'])])
            if not category:
                category = category_obj.create({
                    'name': res['categ_name']
                })

            # 创建单位
            uom = uom_obj.search([('name', '=', res['unit'])])
            if not uom:
                uom_categ = uom_categ_obj.create({
                    'name': res['unit']
                })
                uom = uom_obj.create({
                    'name': res['unit'],
                    'category_id': uom_categ.id,

                })



            # 创建产品
            product_template_obj.create({
                'categ_id': category.id, # 内部分类
                'name': res['name'], # 产品名称
                'sale_ok': True,
                'purchase_ok': False,
                'type': 'service',
                'list_price': res['list_price'],
                'his_id': res['his_id'],
                'uom_id': uom.id,
                'uom_po_id': uom.id,
                'fee_name': res['fee_name'],
                'code': res['code'], # HIS编码
            })


    def product_insert(self, result):
        self.product_template(result)


    @classmethod
    def on_product_notify(cls, message):
        row_ids = SyncDefine.merge_notify_rowid(message, SyncProduct.his_table_name, cx_Oracle.OPCODE_INSERT)

        if not row_ids:
            return

        db_name = config['db_name']
        db = odoo.sql_db.db_connect(db_name)
        cr = db.cursor()

        try:
            registry = odoo.registry(db_name)
            notify_data_id = registry[cls._name].product_notify(row_ids, cr)
            cr.commit()
            SyncProduct.query_queue.put(notify_data_id)  # 放入查询队列
        except Exception:
            cr.rollback()
            _logger.info(u'处理%s通知出错，行IDS:%s', SyncProduct.his_table_name, row_ids)
            _logger.error(traceback.format_exc())
        finally:
            cr.close()


    @classmethod
    def product_notify(cls, row_ids, cr):
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            notify_data_id = self.process_product_notify(row_ids)

        return notify_data_id


    @api.model
    def process_product_notify(self, row_ids):
        notify_data = self.env['his.notify_data'].create_notify_data(row_ids, SyncProduct.his_table_name, 'insert') # 插入notify_data
        return notify_data.id


    @classmethod
    def start_process_query_queue_product(cls):
        """数据改变通知队列处理"""
        db_name = config['db_name']
        db = odoo.sql_db.db_connect(db_name)
        cr = db.cursor()

        registry = odoo.registry(db_name)
        # 将未处理的通知放入队列
        try:
            registry[cls._name].get_no_process_product_queue(cr)
        except Exception:
            cr.rollback()
            _logger.exception(u'将%s未处理的通知放入队列出错!', SyncProduct.his_table_name)
            _logger.error(traceback.format_exc())
        finally:
            cr.close()

        while True:
            notify_data_id = SyncProduct.query_queue.get()
            cr = db.cursor()
            try:
                registry[cls._name].process_notify_product(notify_data_id, cr)
                cr.commit()
                time.sleep(0.5)
            except Exception:
                cr.rollback()
                _logger.error(u'处理%s通知%s出错', SyncProduct.his_table_name, notify_data_id)
                _logger.error(traceback.format_exc())
                time.sleep(5)
                SyncProduct.query_queue.put(notify_data_id)
            finally:
                cr.close()


    @classmethod
    def get_no_process_product_queue(cls, cr):
        """将未处理的通知放入队列"""
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            self.no_process_product_in_queue()


    @api.model
    def no_process_product_in_queue(self):
        """将未处理的通知放入队列"""
        for notify_data in self.env['his.notify_data'].search([('state', '=', 'draft'), ('sync_id', '=', self.search([('name', '=', SyncProduct.his_table_name)]).id)], order='id asc'):
            SyncProduct.query_queue.put(notify_data.id)


    @classmethod
    def process_notify_product(cls, notify_data_id, cr):
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            self.process_query_product(notify_data_id)


    @api.model
    def process_query_product(self, notify_data_id):
        ora_obj = Ora()

        notify_data = self.env['his.notify_data'].browse(notify_data_id)

        row_ids = notify_data.row_ids.split(',')
        in_vars = ','.join(':%d' % i for i in xrange(len(row_ids)))

        query_result = ora_obj.query(notify_data.sync_id.insert_query_sql % in_vars, args=row_ids)

        if query_result:
            self.product_insert(query_result)

        notify_data.write({
            'query_result': json.dumps(query_result, ensure_ascii=False, encoding='utf8', indent=4),
            'state': 'done'
        })


