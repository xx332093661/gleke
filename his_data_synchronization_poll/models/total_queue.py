# -*- encoding:utf-8 -*-
from odoo import models, fields



class TotalQueue(models.Model):
    _inherit = 'hrp.total_queue'

    origin_table = fields.Char('来源表')
    origin_id = fields.Integer('来源ID')

    _sql_constraints = [('origin_table_origin_id_uniq', 'unique (origin_table, origin_id, business)', u'数据来源必须唯一!')]


    def queue_exist(self, origin_table, origin_id):
        """队列是否存在"""
        return self.search([('origin_table', '=', origin_table), ('origin_id', '=', origin_id)])

