# -*- encoding:utf-8 -*-
from odoo import models, fields
from odoo import api
from odoo.exceptions import Warning


class ScheduleDepartmentEmployee(models.Model):
    _name = 'his.schedule_department_employee'
    _description = '科室排班人员'
    update_external = True  # 更新外部服务器数据

    department_id = fields.Many2one('hr.department', '科室')
    employee_id = fields.Many2one('hr.employee', '人员', required=True)
    register_time_interval = fields.Char('挂号间隔(分钟)', default='5', required=True)
    room_id = fields.Many2one('hr.department', '坐诊诊室')
    register_type = fields.Char('号类(挂号安排号类)')
    as_rowid = fields.Char('号码(挂号安排号码)')
    queue_prefix = fields.Char('队列前缀')
    allow_free = fields.Boolean('允许服务券支付')
    free_as_rowid = fields.Char('服务券号码(挂号安排号码)')
    free_register_type = fields.Char('服务券号类(挂号安排号码)')
    his_id = fields.Integer('HISID')
    employee_register_limit = fields.One2many('his.employee_register_limit', 'schedule_department_employee_id', '限号')
    product_ids = fields.Many2many('product.template', 'his_employee_register_product_rel', 'schedule_department_employee_id', 'product_template_id', '挂号收费项目')

    _sql_constraints = [
        ('department_id_employee_id_uniq', 'unique (department_id, employee_id)', u'排班医生重复'),
        ('department_id_employee_id_uniq', 'unique (department_id, queue_prefix)', u'队列前缀重复'),
    ]

    @api.model
    def create(self, vals):
        register_time_interval = vals['register_time_interval']
        for a in register_time_interval.split(','):
            try:
                int(a)
            except ValueError:
                raise Warning('挂号时间间接必须是以英文逗号间接的数字')

        return super(ScheduleDepartmentEmployee, self).create(vals)

    @api.multi
    def write(self, vals):
        return super(ScheduleDepartmentEmployee, self).write(vals)

    @api.multi
    def unlink(self):
        return super(ScheduleDepartmentEmployee, self).unlink()



class EmployeeRegisterLimit(models.Model):
    _name = 'his.employee_register_limit'
    _description = '限号'
    update_external = True  # 更新外部服务器数据

    @api.model
    def _default_get_limit_type(self):
        if 'employee_register_limit' in self.env.context:
            for employee_register_limit in self.env.context['employee_register_limit']:
                if employee_register_limit[0] == 4:
                    return self.browse(employee_register_limit[1]).limit_type

                if employee_register_limit[0] == 0:
                    return employee_register_limit[2]['limit_type']

        return None

    schedule_department_employee_id = fields.Many2one('his.schedule_department_employee', '排班人员', ondelete='cascade')
    department_id = fields.Many2one('hr.department', '科室', default=lambda self: self._context.get('department_id'))
    employee_id = fields.Many2one('hr.employee', '人员', default=lambda self: self._context.get('employee_id'))
    limit_type = fields.Selection([('shift', '班次限号'), ('all', '全天限号')], '限号方式', required=True, default=_default_get_limit_type)
    shift_type_id = fields.Many2one('his.shift_type', '班次')
    limit = fields.Integer('限号数', required=True)

    _sql_constraints = [
        ('department_employee_shift_type_uniq', 'unique(schedule_department_employee_id, shift_type_id)', '限号班次重复!'),
    ]


    @api.model
    def create(self, vals):
        if vals['limit'] < 1:
            raise Warning('限号数必须大于0!')

        if vals['limit_type'] == 'all':
            if self.search([('schedule_department_employee_id', '=', vals['schedule_department_employee_id']), ('limit_type', '=', vals['limit_type'])]):
                raise Warning('限号设置重复!')

        return super(EmployeeRegisterLimit, self).create(vals)


    @api.multi
    def write(self, vals):
        if 'limit' in vals and vals['limit'] < 1:
            raise Warning('限号数必须大于0!')

        return super(EmployeeRegisterLimit, self).write(vals)


    @api.multi
    def unlink(self):
        return super(EmployeeRegisterLimit, self).unlink()








