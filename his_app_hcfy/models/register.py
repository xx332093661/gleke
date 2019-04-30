# -*- encoding:utf-8 -*-
from odoo import api
from odoo import models, fields


class Register(models.Model):
    _inherit = 'his.register'
    _description = 'HIS挂号记录'

    reserve_record_ids = fields.One2many('his.reserve_record', 'register_id', '预约记录')
    operator_code = fields.Char('操作员编号')

    reserve_date = fields.Date('就诊日期')
    tran_flow = fields.Char('医院结算流水号')
    register_no = fields.Char('HIS挂号单号')
    department_id = fields.Many2one('hr.department', '科室')
    employee_id = fields.Many2one('hr.employee', '医生', required=False)
    register_type = fields.Char('号类')
    as_rowid = fields.Char('号码')



