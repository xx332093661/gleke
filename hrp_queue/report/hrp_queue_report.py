# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo import tools
from ..models.hrp_queue import STATE


class HrpTotalQueueReport(models.Model):
    _name = 'hrp.total_queue_report'
    _auto = False
    _description = u'总队列报表'
    _rec_name = 'date'

    outpatient_num = fields.Char('门诊号', readonly=True)
    partner_id = fields.Many2one('res.partner', '患者', readonly=True)
    business = fields.Char('业务类型', readonly=True)
    department_id = fields.Many2one('hr.department', '科室', readonly=True)
    room_id = fields.Many2one('hr.department', '诊室', readonly=True)
    employee_id = fields.Many2one('hr.employee', '挂号医生', readonly=True)
    register_type = fields.Char('号类', readonly=True)
    origin = fields.Selection([('1', '门诊'), ('2', '住院')], '病人来源')
    date = fields.Datetime('时间', readonly=True)
    count = fields.Integer('数量')

    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, self._table)
        sql = """CREATE OR REPLACE VIEW %s AS (
                    select
                        w.id,
                        w.outpatient_num,
                        w.partner_id,
                        w.business,
                        w.department_id,
                        w.room_id,
                        w.employee_id,
                        w.register_type,
                        w.origin,
                        w.enqueue_datetime as date,
                        1 as count
                    from
                        hrp_total_queue w
                )""" % self._table
        cr.execute(sql)


class HrpQueueReport(models.Model):
    _name = 'hrp.queue_report'
    _auto = False
    _description = u'分诊队列报表'
    _rec_name = 'date'

    outpatient_num = fields.Char('门诊号', readonly=True)
    partner_id = fields.Many2one('res.partner', '患者', readonly=True)
    business = fields.Char('业务类型', readonly=True)
    department_id = fields.Many2one('hr.department', '科室', readonly=True)
    room_id = fields.Many2one('hr.department', '诊室', readonly=True)
    employee_id = fields.Many2one('hr.employee', '挂号医生', readonly=True)
    register_type = fields.Char('号类', readonly=True)
    origin = fields.Selection([('1', '门诊'), ('2', '住院')], '病人来源')
    date = fields.Datetime('时间', readonly=True)
    count = fields.Integer('数量')

    state = fields.Selection(STATE, '队列状态', readonly=True)
    stage = fields.Selection([('1', '初诊'), ('2', '回诊')], '就诊阶段', readonly=True)
    operation_room_id = fields.Many2one('hr.department', '执行诊室', readonly=True)
    operation_employee_id = fields.Many2one('hr.employee', '执行医生', readonly=True)

    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, self._table)
        sql = """CREATE OR REPLACE VIEW %s AS (
                    select
                        w.id,
                        w.outpatient_num,
                        w.partner_id,
                        w.business,
                        w.department_id,
                        w.room_id,
                        w.employee_id,
                        w.register_type,
                        w.origin,
                        w.enqueue_datetime as date,
                        1 as count,
                        w.state,
                        w.stage,
                        w.operation_room_id,
                        w.operation_employee_id
                    from
                        hrp_queue w
                )""" % self._table
        cr.execute(sql)