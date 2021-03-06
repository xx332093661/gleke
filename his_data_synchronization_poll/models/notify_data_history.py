# -*- encoding:utf-8 -*-
from odoo import models, fields



class NotifyDataHistory(models.Model):
    _name = 'his.notify_data_history'
    _description = '通知数据'
    _order = 'id desc'

    # parent_id = fields.Many2one('his.notify_data_all', '所有通知数据')

    sync_id = fields.Many2one('his.sync_define', '同步定义')

    operation = fields.Selection([('insert', '插入'), ('update', '更新')], '操作')
    row_ids = fields.Text('行ID')

    # query_date = fields.Datetime('查询时间')
    query_result = fields.Text('查询结果')

    # process_date = fields.Datetime('查询处理时间')

    state = fields.Selection([('draft', '通知'), ('done', '完成')], '状态', index=True, default='draft')

    is_history = fields.Boolean('历史记录')















