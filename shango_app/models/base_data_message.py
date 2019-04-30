# -*- encoding:utf-8 -*-
import json

from odoo import fields, models


class BaseDataMessage(models.Model):
    _name = 'his.base_data_message'
    _description = '基础数据通知消息'
    _rec_name = 'identifier'
    _order = 'id desc'

    payload = fields.Text('有效载荷')
    action = fields.Char('动作')
    state = fields.Selection([('draft', '未处理'), ('done', '已处理')], '状态', default='draft')
    company_id = fields.Many2one('res.company', '医院')
    source_topic = fields.Char('消息来源主题')
    accept_topic = fields.Char('消息接收主题')
    identifier = fields.Char('标识符')
    msg_type = fields.Selection([('accept', '接收'), ('send', '发送')], '消息类型')
    token = fields.Char('令牌')
    mac = fields.Char('MAC')



    def create_message(self, payload, msg_type):
        """创建消息记录"""
        m_company = self.env['res.company']
        # 根据消息来源获取医院
        source_topic = payload['source_topic']
        company = m_company.search([('topic', '=', source_topic)])
        company_id = company.id if company else False

        return self.create({
            'payload': json.dumps(payload['data'], ensure_ascii=False, encoding='utf8', indent=4),
            'action': payload['action'],
            'state': 'done',
            'source_topic': source_topic,
            'identifier': payload['identifier'],
            'msg_type': msg_type,
            'mac': payload['mac'],
            'token': payload['token'],
            'company_id': company_id,
        })

    # def filer_message(self, msg):
    #     """判断消息是否重复"""
    #     if not msg.get('identifier'):
    #         return
    #     if self.search([('identifier', '=', msg['identifier']), ('source_topic', '=', msg.get('source_topic'))]):
    #         # 消息重复
    #         return
    #     return msg
