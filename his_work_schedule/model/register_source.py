# -*- encoding:utf-8 -*-
from datetime import datetime, timedelta

from odoo import api
from odoo import fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import Warning


class RegisterSource(models.Model):
    _name = 'his.register_source'
    _description = '挂号号源'
    update_external = True  # 更新外部服务器数据
    _rec_name = 'time_point_name'

    shift_id = fields.Many2one('his.schedule_shift', '班次', ondelete='cascade')
    time_point_name = fields.Char('时间点')
    state = fields.Selection([('0', '待预约'), ('1', '已预约'), ('2', '锁定')], '状态', default='0')
    readonly = fields.Boolean(compute='_compute_readonly', string='是否只读')

    department_id = fields.Many2one('hr.department', '科室', store=True, related='shift_id.department_id')
    employee_id = fields.Many2one('hr.employee', '医生', store=True, related='shift_id.employee_id')
    # expired = fields.Boolean(compute='get_expired', string='是否过期')
    date = fields.Date('日期', store=True, related='shift_id.schedule_id.date')
    shift_type_id = fields.Many2one('his.shift_type', '班次', store=True, related='shift_id.shift_type_id')

    lock_time = fields.Datetime('锁定时间')


    @api.multi
    @api.depends('shift_id', 'state')
    def _compute_readonly(self):
        for obj in self:
            if obj.state != '0' or obj.shift_id.is_stop:
                obj.readonly = True
            else:
                try:
                    time_point_name = datetime.strptime('%s %s:00' % (obj.shift_id.schedule_id.date, obj.time_point_name), DEFAULT_SERVER_DATETIME_FORMAT) - timedelta(hours=8)
                    if datetime.now() > time_point_name:
                        obj.readonly = True
                    else:
                        obj.readonly = False
                except ValueError:
                    obj.readonly = False


    @api.model
    def delete_register_source(self, *_, **kwargs):
        """删除号源"""
        register_source = self.browse(kwargs['id'])
        if register_source.state != '0':
            raise Warning('号源已被预约，不能删除!')

        register_source.unlink()



