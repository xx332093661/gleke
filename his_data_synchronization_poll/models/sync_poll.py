# -*- encoding:utf-8 -*-
import json
import logging
import threading
import time
from datetime import datetime, timedelta
import traceback

from odoo import api
from odoo import models
from odoo.addons.his_data_synchronization_poll.ora import Ora
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class SyncPoll(models.Model):
    _inherit = 'his.sync_define'


    def poll(self):
        """轮询数据"""
        t = threading.Thread(target=self.start_poll, args=[], name='start_poll_thread')
        t.setDaemon(True)
        t.start()



    def start_poll(self):
        """开启处理轮询线程"""
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            while True:
                self.process_poll()


    @api.model
    def process_poll(self):
        ora_obj = Ora()

        poll_data_obj = self.env['his.poll_data'] # 轮询数据

        for sync in self.search([('active', '=', True), ('is_poll', '=', True)], order='query_sort asc'):
            arg = datetime.strptime(sync.key_field_last_value, DEFAULT_SERVER_DATETIME_FORMAT) - timedelta(seconds=sync.rollback_value)
            # _logger.info(u'正在轮询%s, 关键字段值:%s, 用以查询的值:%s', sync.name, sync.key_field_last_value, arg.strftime(DEFAULT_SERVER_DATETIME_FORMAT))

            try:
                values = ora_obj.query(sync.poll_sql, args=[arg])

                if values:
                    getattr(self, sync.poll_callback)(values, sync)

                    poll_data_obj.create({
                        'query_result': json.dumps(values, ensure_ascii=False, indent=4),
                        'sync_id': sync.id,
                    })

                    self.env.cr.commit() # 提交
            except:
                _logger.error(u'轮询%s错误', sync.name)
                _logger.error(traceback.format_exc())

            time.sleep(sync.poll_interval)

        return {}











