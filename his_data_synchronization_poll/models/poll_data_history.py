# -*- encoding:utf-8 -*-
from odoo import models, fields



class PollDataHistory(models.Model):
    _name = 'his.poll_data_history'
    _description = '轮询数据'
    _order = 'id desc'

    query_result = fields.Text('查询结果')

    sync_id = fields.Many2one('his.sync_define', '同步定义')
    is_history = fields.Boolean('历史记录')

    # process_date = fields.Datetime('查询处理时间')

    # state = fields.Selection([('query', '查询'), ('done', '完成')], '状态')