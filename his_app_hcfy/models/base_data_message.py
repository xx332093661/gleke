# -*- encoding:utf-8 -*-
from odoo import fields, models


class BaseDataMessage(models.Model):
    _name = 'his.base_data_message'
    _description = '基础数据通知消息'
    _order = 'id desc'

    payload = fields.Text('有效载荷')
    action = fields.Char('动作')
    state = fields.Selection([('draft', '未处理'), ('done', '已处理')], '状态', default='draft')
    # company_id = fields.Many2one('res.company', '医院')
    source_topic = fields.Char('来源主题')
    accept_topic = fields.Char('接收主题')
    identifier = fields.Char('标识符')
    msg_type = fields.Selection([('accept', '接收'), ('send', '发送')], '消息类型')
    token = fields.Char('令牌')
    mac = fields.Char('MAC')

    refund_apply_id = fields.Many2one('his.refund_apply', '退款申请')
