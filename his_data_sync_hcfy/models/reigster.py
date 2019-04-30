# -*- encoding:utf-8 -*-
from odoo import api
from odoo import models, fields


class Register(models.Model):
    _name = 'his.register'
    _description = '病人挂号记录'
    _order = 'id desc'

    # TODO 创建索引 名称:his_register_receipt_no_partner_id 字段;receipt_no, partner_id

    his_id = fields.Integer('HISID', index=True)
    receipt_no = fields.Char('单据号')
    record_state = fields.Integer('记录状态')
    exe_state = fields.Integer('执行状态')
    register_type = fields.Char('号类')

    employee_id = fields.Many2one('hr.employee', '医生')
    department_id = fields.Many2one('hr.department', '执行部门')
    is_emerg_treat = fields.Boolean('急诊')
    # room_name = fields.Char('诊室')
    # fee_name = fields.Char('收费项目名称')
    register_datetime = fields.Char('登记时间')
    register_date = fields.Date('发生日期', help='通过"发生时间"计算出来')

    partner_id = fields.Many2one('res.partner', '病人')

    total_queue_id = fields.Many2one('hrp.total_queue', '总队列')

    is_history = fields.Boolean('历史记录')


    @api.model
    def his_id_exist(self, his_id):
        return self.search([('his_id', '=', his_id)])
