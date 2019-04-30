# -*- encoding:utf-8 -*-
from odoo import fields, models


class ReserveRecord(models.Model):
    _description = u'预约记录'
    _name = 'his.reserve_record'
    _order = 'id desc'

    partner_id = fields.Many2one('res.partner', '患者')
    reserve_date = fields.Date('就诊日期')
    department_id = fields.Many2one('hr.department', '科室')
    employee_id = fields.Many2one('hr.employee', '医生')

    shift_type_id = fields.Many2one('his.shift_type', '班次')
    register_source_id = fields.Many2one('his.register_source', '号源')
    # time_point_name = fields.Char('时间点')
    reserve_sort = fields.Char('预约顺序号')

    order_id = fields.Many2one('sale.order', '订单')
    register_id = fields.Many2one('his.register', 'HIS挂号记录')
    type = fields.Selection([('register', '挂号'), ('inoculation', '预防接种'), ('pregnant', '产检'), ('', '体检')], '类别')
    state = fields.Selection([('draft', '草稿'), ('reserve', '预约'), ('commit', '提交HIS'), ('done', '完成'), ('cancel', '取消')], '状态')

    commit_his_state = fields.Selection([('-1', '未提交'), ('0', '提交HIS失败'), ('1', '提交HIS成功')], '提交HIS状态', default='-1')
    cancel_type = fields.Selection([('1', '用户取消'), ('2', '停诊取消')], '取消类别')

    company_id = fields.Many2one('res.company', '医院')
    internal_id = fields.Integer('内部ID')