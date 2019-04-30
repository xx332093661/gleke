# -*- encoding:utf-8 -*-
import logging
import threading
import traceback

from odoo import api
from odoo import models, fields

_logger = logging.getLogger(__name__)


class Dispose(models.Model):
    _name = 'his.dispose'
    _description = '病人医嘱记录'
    _order = 'id desc'
    create_lock = threading.Lock()

    his_id = fields.Integer('HISID', index=True, help='医嘱ID')

    relation_dispose_id = fields.Integer('相关ID')
    # parent_id = fields.Many2one('his.dispose', '父医嘱', help='由相关ID计算出来')
    receipt_no = fields.Char('挂号单')
    clinic_type = fields.Char('诊疗类别')
    item_id = fields.Many2one('his.clinic_item_category', '诊疗项目ID')
    part = fields.Char('标本部位')
    method = fields.Char('检查方法')
    department_id = fields.Many2one('hr.department', '执行科室')
    origin = fields.Integer('病人来源')
    dispose_datetime = fields.Char('开嘱时间')
    dispose_date = fields.Char('开嘱日期')
    amount_total = fields.Float('总给予量')
    days = fields.Float('天数')
    frequency = fields.Integer('频率次数')
    frequency_interval = fields.Integer('频率间隔')
    interval_unit = fields.Char('间隔单位')

    partner_id = fields.Many2one('res.partner', '病人')

    total_queue_id = fields.Many2one('hrp.total_queue', '总队列')

    is_history = fields.Boolean('历史记录')

    _sql_constraints = [('his_id_uniq', 'unique (his_id)', u'his_id必须唯一!')]


    @api.model
    def his_id_exist(self, his_id):
        return self.search([('his_id', '=', his_id)])

    @api.model
    def create(self, vals):
        with Dispose.create_lock:
            dispose = self.his_id_exist(vals['his_id'])
            if not dispose:
                try:
                    dispose = super(Dispose, self).create(vals)
                    self.env.cr.commit()
                except:
                    self.env.cr.rollback()
                    _logger.warn(u'创建病人医嘱记录出错')
                    _logger.error(traceback.format_exc())
                    dispose = self.his_id_exist(vals['his_id'])

        return dispose





