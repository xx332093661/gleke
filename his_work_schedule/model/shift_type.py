# -*- encoding:utf-8 -*-
from odoo import api, exceptions
from odoo import fields, models


class ShiftType(models.Model):
    _name = 'his.shift_type'
    _description = '班次类型'
    update_external = True  # 更新外部服务器数据

    @api.model
    def _default_name(self):
        if self._context['is_outpatient']: # 门诊不参与默认值计算
            return None

        shift_type_ids = self._context['shift_type_ids']
        if not shift_type_ids:
            return '上午'

        shift_type_ids = filter(lambda x: x[0] in [4, 0], shift_type_ids)
        if not shift_type_ids:
            return '上午'

        shift_type = shift_type_ids[-1]
        if shift_type[0] == 4:
            shift = self.browse(shift_type[1])
            if shift.name == u'上午':
                return '下午'

            return '上午'

        if shift_type[0] == 0:
            shift = shift_type[2]
            if shift['name'] == u'上午':
                return '下午'

            return '上午'

        return None

    @api.model
    def _default_label(self):
        if self._context['is_outpatient']:  # 门诊不参与默认值计算
            return None

        shift_type_ids = self._context['shift_type_ids']
        if not shift_type_ids:
            return '上'

        shift_type_ids = filter(lambda x: x[0] in [4, 0], shift_type_ids)
        if not shift_type_ids:
            return '上'

        shift_type = shift_type_ids[-1]
        if shift_type[0] == 4:
            shift = self.browse(shift_type[1])
            if shift.label == u'上':
                return '下'

            return '上'

        if shift_type[0] == 0:
            shift = shift_type[2]
            if shift['label'] == u'上':
                return '下'

            return '上'

        return None

    @api.model
    def _default_start_time(self):
        if self._context['is_outpatient']:  # 门诊不参与默认值计算
            return 0

        shift_type_default_obj = self.env['his.shift_type_default']
        shift_type_ids = self._context['shift_type_ids']
        if not shift_type_ids:
            shift_type_default = shift_type_default_obj.search([('name', '=', u'上午')])
            if shift_type_default:
                return shift_type_default.start_time
            return 0

        shift_type_ids = filter(lambda x: x[0] in [4, 0], shift_type_ids)
        if not shift_type_ids:
            shift_type_default = shift_type_default_obj.search([('name', '=', u'上午')])
            if shift_type_default:
                return shift_type_default.start_time
            return 0

        shift_type = shift_type_ids[-2:]
        if len(shift_type) == 1:
            shift = shift_type[0]
            if shift[0] == 4:
                shift = self.browse(shift[1])
                if shift.name == u'上午':
                    shift_type_default = shift_type_default_obj.search([('name', '=', u'下午')])
                    if shift_type_default:
                        return shift_type_default.start_time
                    return 0

                if shift.name == u'下午':
                    shift_type_default = shift_type_default_obj.search([('name', '=', u'上午')])
                    if shift_type_default:
                        return shift_type_default.start_time
                    return 0

            if shift[0] == 0:
                shift = shift[2]
                if shift['name'] == u'上午':
                    shift_type_default = shift_type_default_obj.search([('name', '=', u'下午')])
                    if shift_type_default:
                        return shift_type_default.start_time
                    return 0

                if shift['name'] == u'下午':
                    shift_type_default = shift_type_default_obj.search([('name', '=', u'上午')])
                    if shift_type_default:
                        return shift_type_default.start_time
                    return 0

            return 0

        else:
            shift = shift_type[0]
            if shift[0] == 4:
                shift = self.browse(shift[1])
                return shift.start_time

            if shift[0] == 0:
                return shift[2]['start_time']

        # return shift_type[0][2]['start_time']


    @api.model
    def _default_end_time(self):
        if self._context['is_outpatient']:  # 门诊不参与默认值计算
            return 0

        shift_type_default_obj = self.env['his.shift_type_default']
        shift_type_ids = self._context['shift_type_ids']
        if not shift_type_ids:
            shift_type_default = shift_type_default_obj.search([('name', '=', u'上午')])
            if shift_type_default:
                return shift_type_default.end_time
            return 0

        shift_type_ids = filter(lambda x: x[0] in [4, 0], shift_type_ids)
        if not shift_type_ids:
            shift_type_default = shift_type_default_obj.search([('name', '=', u'上午')])
            if shift_type_default:
                return shift_type_default.end_time
            return 0

        shift_type = shift_type_ids[-2:]
        if len(shift_type) == 1:
            shift = shift_type[0]
            if shift[0] == 4:
                shift = self.browse(shift[1])
                if shift.name == u'上午':
                    shift_type_default = shift_type_default_obj.search([('name', '=', u'下午')])
                    if shift_type_default:
                        return shift_type_default.end_time
                    return 0

                if shift.name == u'下午':
                    shift_type_default = shift_type_default_obj.search([('name', '=', u'上午')])
                    if shift_type_default:
                        return shift_type_default.end_time
                    return 0

            if shift[0] == 0:
                shift = shift[2]
                if shift['name'] == u'上午':
                    shift_type_default = shift_type_default_obj.search([('name', '=', u'下午')])
                    if shift_type_default:
                        return shift_type_default.end_time
                    return 0

                if shift['name'] == u'下午':
                    shift_type_default = shift_type_default_obj.search([('name', '=', u'上午')])
                    if shift_type_default:
                        return shift_type_default.end_time
                    return 0

            return 0

        else:
            shift = shift_type[0]
            if shift[0] == 4:
                shift = self.browse(shift[1])
                return shift.end_time

            if shift[0] == 0:
                return shift[2]['end_time']

        return 0


    @api.model
    def _default_max_execute_count(self):
        if self._context['is_outpatient']:  # 门诊不参与默认值计算
            return 0

        shift_type_ids = self._context['shift_type_ids']
        if not shift_type_ids:
            return 0

        shift_type_ids = filter(lambda x: x[0] in [4, 0], shift_type_ids)
        if not shift_type_ids:
            return 0

        shift_type = shift_type_ids[-1]
        if shift_type[0] == 4:
            shift = self.browse(shift_type[1])
            return shift.max_execute_count

        if shift_type[0] == 0:
            shift = shift_type[2]
            return shift['max_execute_count']

        return 0

    name = fields.Char('名称', required=False, default=_default_name)
    department_id = fields.Many2one('hr.department', '科室', required=True)
    week_name = fields.Selection([('1', '星期一'), ('2', '星期二'), ('3', '星期三'), ('4', '星期四'), ('5', '星期五'), ('6', '星期六'), ('0', '星期日')], '星期')
    max_execute_count = fields.Integer('最大执行数量', default=_default_max_execute_count)
    start_time = fields.Float('上班时间', required=False, default=_default_start_time)
    end_time = fields.Float('下班班时间', required=False, default=_default_end_time)
    color = fields.Char('颜色', default='#eeeeee')
    label = fields.Char('显示', default=_default_label)
    type = fields.Selection([('1', '工作'), ('2', '非工作')], '班次类型', default='1')


    @api.multi
    def set_default_shift_type(self):
        department_id = self.department_id.id
        self.search([('department_id', '=', department_id)]).unlink()
        for shift in self.env['his.shift_type_default'].search([]):
            self.create({
                'department_id': department_id,
                'name': shift.name,
                'start_time': shift.start_time,
                'end_time': shift.end_time,
                'color': shift.color,
                'label': shift.label,
                'type': shift.type
            })
        return {
            'name': '班次类型',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'his.shift_type',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

    @api.model
    def create(self, vals):
        department = self.env['hr.department'].browse(vals['department_id'])
        if department.is_outpatient:
            vals['week_name'] = False
            vals['max_execute_count'] = 0
        # else:
        #     if not vals['week_name']:
        #         raise exceptions.Warning(u"排班记录请选择星期!")
        #
        #     if vals['max_execute_count'] < 1:
        #         raise exceptions.Warning(u"排班记录请输入最大执行数量!")

        return super(ShiftType, self).create(vals)


    @api.multi
    def write(self, vals):
        department = self.department_id
        if department.is_outpatient:
            if 'week_name' in vals:
                vals['week_name'] = False
            if 'max_execute_count' in vals:
                vals['max_execute_count'] = 0
        # else:
        #     if 'week_name' in vals and not vals['week_name']:
        #         raise exceptions.Warning(u"排班记录请选择星期!")
        #
        #     if 'max_execute_count' in vals and vals['max_execute_count'] < 1:
        #         raise exceptions.Warning(u"排班记录请输入最大执行数量!")

        return super(ShiftType, self).write(vals)

