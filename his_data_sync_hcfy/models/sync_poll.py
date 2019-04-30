# -*- encoding:utf-8 -*-
import json
import logging
import threading
import time
from datetime import datetime, timedelta
import traceback

import odoo
from odoo import api
from odoo import models
from odoo.addons.his_data_synchronization_poll.ora import Ora
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, config

_logger = logging.getLogger(__name__)


class SyncPoll(models.Model):
    _inherit = 'his.sync_define'


    def poll(self):
        """轮询数据"""
        t = threading.Thread(target=self.start_poll, args=[], name='start_poll_thread')
        t.setDaemon(True)
        t.start()


    @classmethod
    def start_poll(cls):
        db_name = config['db_name']
        db = odoo.sql_db.db_connect(db_name)
        cr = db.cursor()
        try:
            registry = odoo.registry(db_name)
            registry[cls._name].start_process_poll(cr)
        except Exception:
            _logger.exception(u'将%s未处理的通知放入队列出错!')
            _logger.error(traceback.format_exc())
        finally:
            cr.close()

    @classmethod
    def start_process_poll(cls, cr):
        with api.Environment.manage():
            self = api.Environment(cr, 1, {})[cls._name]
            while True:
                self.process_poll()


    @api.model
    def process_poll(self):
        ora_obj = Ora()

        poll_data_obj = self.env['his.poll_data'] # 轮询数据

        for sync in self.search([('active', '=', True), ('is_poll', '=', True)], order='query_sort asc'):
            arg = datetime.strptime(sync.key_field_last_value, DEFAULT_SERVER_DATETIME_FORMAT) - timedelta(seconds=sync.rollback_value)
            # if sync.name_en == 'dispose_send':
            #     _logger.info(u'正在轮询%s, 开始轮询', sync.name)

            try:
                name_en = None
                # if sync.name_en == 'dispose_send':
                #     name_en = 'dispose_send'
                values = ora_obj.query(sync.poll_sql, args=[arg], name_en=name_en)

                # if sync.name_en == 'dispose_send':
                #     _logger.info(u'正在轮询%s, HIS返回记录数:%s', sync.name, len(values))

                if values:
                    getattr(self, sync.poll_callback)(values, sync)

                    # if sync.name_en == 'dispose_send':
                    #     _logger.info(u'正在轮询%s, 同步数据处理完成', sync.name)

                    poll_data_obj.create({
                        'query_result': json.dumps(values, ensure_ascii=False, indent=4),
                        'sync_id': sync.id,
                    })

                    self.env.cr.commit() # 提交
                    # if sync.name_en == 'dispose_send':
                    #     _logger.info(u'正在轮询%s, 提交完成', sync.name)
            except:
                self.env.cr.rollback()  # 提交
                _logger.error(u'轮询%s错误', sync.name)
                _logger.error(traceback.format_exc())

            # if sync.name_en == 'dispose_send':
            #     _logger.info(u'正在轮询%s, 结束轮询', sync.name)

            time.sleep(sync.poll_interval)

        return {}











