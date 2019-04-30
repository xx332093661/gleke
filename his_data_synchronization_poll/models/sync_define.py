# -*- encoding:utf-8 -*-
import logging
import os
import threading
import cx_Oracle
from datetime import datetime, timedelta

from odoo import api
from odoo import models, fields
from odoo.tools import config, DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'


class SyncDefine(models.Model):
    _name = 'his.sync_define'
    _description = 'Oracle数据同步定义'
    _order = 'query_sort asc'

    sync_started = False # 是否已开启同步



    ora_conn = None # 数据库连接
    ora_subscribe = [] # 数据库订阅对象

    active = fields.Boolean('Active', default=True)

    name = fields.Char(string='HIS表名', required=True)
    name_en = fields.Char('HIS表名英文标识')
    is_base = fields.Boolean('是否是基础数据')
    is_poll = fields.Boolean('是否轮询')
    is_notify = fields.Boolean('是否通知')
    query_sort = fields.Integer('查询顺序')



    subscribe_sql = fields.Char('订阅SQL')
    subscribe_date = fields.Datetime('最近订阅时间')
    subscribe_type = fields.Many2many('his.subscribe_type', 'notify_subscribe_type_rel', 'subscribe_id', 'type_id', string='订阅类型', help='数据库表的动作类型')

    notify_data = fields.One2many('his.notify_data', 'sync_id', '通知数据')
    poll_data = fields.One2many('his.poll_data', 'sync_id', '轮询数据')


    insert_query_sql = fields.Text('Insert查询SQL')
    update_query_sql = fields.Text('Update查询SQL')
    base_sql = fields.Text('基础数据同步SQL')

    insert_query_callback = fields.Char('Insert查询回调函数')
    update_query_callback = fields.Char('Update查询回调函数')
    base_query_callback = fields.Char('基础数据查询回调函数')
    notify_callback = fields.Char('Oracle通知回调函数')
    show_insert = fields.Boolean()
    show_update = fields.Boolean()



    poll_sql = fields.Text('轮询SQL')
    # last_poll_date = fields.Datetime('最近一次轮询时间', default=fields.Datetime.now)
    key_field_last_value = fields.Char('关键字段最新值')
    key_field_name = fields.Char('关键字段名称')
    poll_callback = fields.Char('轮询回调函数')
    poll_interval = fields.Integer('轮询时间间隔', help='单位秒', default=5)
    rollback_value = fields.Integer('关键字段回滚值', default=5)


    @api.model
    def create(self, vals):
        if vals.get('is_poll'):
            vals['key_field_last_value'] = (datetime.now() + timedelta(hours=8)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return super(SyncDefine, self).create(vals)


    @api.onchange('subscribe_type')
    def onchange_subscribe_type(self):
        self.show_insert = False
        self.show_update = False
        assert isinstance(self.subscribe_type, list)
        for s_type in self.subscribe_type:
            if s_type.subscribe_type == 'OPCODE_INSERT':
                self.show_insert = True
            if s_type.subscribe_type == 'OPCODE_UPDATE':
                self.show_update = True


    def subscribe(self):
        """订阅数据改变通知"""

        syncs = self.search([('active', '=', True), ('is_notify', '=', True)])
        if not syncs:
            return

        # 数据库连接对象
        SyncDefine.ora_conn = cx_Oracle.Connection('%s/%s@%s/%s' % (config['orcl_username'], config['orcl_pwd'], config['orcl_ip'], config['orcl_instance']), events=True)

        for sync in syncs:
            operations = []
            for subscribe_type in sync.subscribe_type:
                operations.append(subscribe_type.subscribe_type)

            if 'OPCODE_INSERT' in operations and 'OPCODE_UPDATE' in operations:
                operations = cx_Oracle.OPCODE_INSERT | cx_Oracle.OPCODE_UPDATE
            elif 'OPCODE_INSERT' in operations:
                operations = cx_Oracle.OPCODE_INSERT
            else:
                operations = cx_Oracle.OPCODE_UPDATE

            notify_callback = getattr(self, sync.notify_callback)
            subscribe = SyncDefine.ora_conn.subscribe(callback=notify_callback, operations=operations, rowids=True)
            subscribe.registerquery(sync.subscribe_sql.encode('utf8'))
            SyncDefine.ora_subscribe.append(subscribe)

            _logger.info(u'订阅%s数据改变通知成功', sync.name)


    @api.model
    def start_sync(self):
        """开启同步线程"""

        if SyncDefine.sync_started: # 是否已开启同步
            return True

        SyncDefine.sync_started = True

        self.poll()  # 轮询
        self.subscribe() # 订阅
        self.start_process_query_queue_thread() # 处理通知消息队列


    @api.model
    def sync_data_history(self):
        """同步数据标记为历史"""
        notify_data_obj = self.env['his.notify_data']
        poll_data_obj = self.env['his.poll_data']

        # today = fields.Date.context_today(self)
        create_date = (datetime.now() - timedelta(days=2)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # 通知数据
        # notify_data_obj.search([('create_date', '<', today), ('is_history', '=', False), ('state', '=', 'done')]).is_history = True
        notify_data_obj.search([('create_date', '<', create_date)]).unlink()

        # 轮询数据
        # poll_data_obj.search([('create_date', '<', today), ('is_history', '=', False)]).is_history = True
        poll_data_obj.search([('create_date', '<', create_date)]).unlink()

        return True



    def start_process_query_queue_thread(self):
        """开启处理通知队列线程"""
        for define in self.search([('active', '=', True), ('is_notify', '=', True)]):
            target = getattr(self, 'start_process_query_queue_' + define.name_en)
            t = threading.Thread(target=target, args=[], name='start_process_query_queue' + define.name_en)
            t.setDaemon(True)
            t.start()


    @api.model
    def sync_base_data(self):
        """同步基础数据"""

        ora_conn = cx_Oracle.Connection('%s/%s@%s/%s' % (config['orcl_username'], config['orcl_pwd'], config['orcl_ip'], config['orcl_instance']))
        ora_cr = ora_conn.cursor()

        for res in self.search([('is_base', '=', True)]):
            ora_cr.execute(res.base_sql)
            columns = [c[0].lower() for c in ora_cr.description] # 字段
            values = ora_cr.fetchall()
            values = [dict(zip(columns, val)) for val in values]
            getattr(self, res.base_query_callback)(values)
            self.env.cr.commit()


        ora_cr.close()
        ora_conn.close()


    @classmethod
    def merge_notify_rowid(cls, message, his_table_name, operation):
        row_ids = []
        for table in message.tables:
            table_name = table.name.decode('utf8').split('.')[1].lower() # "ZLHIS.病人挂号记录" 这时只要"病人挂号记录"
            if table_name != his_table_name:
                continue

            for row in table.rows:
                if row.operation != operation:
                    continue

                if row.rowid not in row_ids:
                    row_ids.append(row.rowid)

        return row_ids
