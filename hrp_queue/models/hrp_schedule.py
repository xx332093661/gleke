# coding:utf-8

from datetime import *
from odoo import models, api, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import random

COLOR = [('#FFB6C1', '浅粉红'), ('#FFC0CB', '粉红'), ('#DC143C', '深红'),
         ('#FFF0F5', '淡紫红'), ('#DB7093', '弱紫罗兰红'), ('#FF69B4', '热情的粉红'),
         ('#FF1493', '深粉红'), ('#C71585', '中紫罗兰红'), ('#DA70D6', '暗紫色'),
         ('#D8BFD8', '蓟色'), ('#DDA0DD', '洋李色'), ('#EE82EE', '紫罗兰'),
         ('#FF00FF', '洋红'), ('#AFEEEE', '弱绿宝石'), ('#00FFFF', '青色'),
         ('#00FFFF', '浅绿色'), ('#00CED1', '暗绿宝石'), ('#E0FFFF', '淡青色'),
         ('#87CEFA', '亮天蓝色'), ('#87CEEB', '天蓝色'), ('#ADD8E6', '亮蓝')]


# AFEEEE PaleTurquoise 弱绿宝石
# 00FFFF Cyan 青色
# 00FFFF Aqua 浅绿色/水色
# 00CED1 DarkTurquoise 暗绿宝石



class HrDepartment(models.Model):
    _inherit = 'hr.department'

    schedule_type_ids = fields.One2many('hrp.schedule_type', 'department_id', '班次')


class HrpScheduleType(models.Model):
    _name = 'hrp.schedule_type'
    _description = u'班次'

    @api.model
    def _get_weekdays(self):
        weekdays = self.env['hrp.schedule_weekday'].search([])
        return weekdays.ids

    @api.model
    def _get_color(self):
        return random.choice(COLOR)[0]

    name = fields.Char('名称')
    department_id = fields.Many2one('hr.department', '科室')
    start = fields.Float('开始时间')
    stop = fields.Float('结束时间')
    total = fields.Float('总时间')
    type = fields.Selection([('1', '工作'), ('2', '非工作'), ('3', '其他')], '班次类型', default='1')
    per_count = fields.Integer('每日人数')
    weekday_ids = fields.Many2many('hrp.schedule_weekday', 'type_weekday_rel', 'type_id', 'weekday_id', '星期', default=_get_weekdays)

    employee_ids = fields.Many2many('hr.employee', 'type_employee_rel', 'type_id', 'employee_id', '员工')
    rule_ids = fields.One2many('hrp.schedule_rule', 'schedule_type_id', '规则')
    color = fields.Selection(COLOR, '颜色', default=_get_color)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if 'department_id' in self._context:
            # 根据科室过滤班次
            args += [('department_id', '=', self._context['department_id'])]
        return super(HrpScheduleType, self).name_search(name=name, args=args, operator=operator, limit=limit)


class HrpScheduleRule(models.Model):
    _name = 'hrp.schedule_rule'
    _description = u'班次规则'

    schedule_type_id = fields.Many2one('hrp.schedule_type', '班次')
    weekday_ids = fields.Many2many('hrp.schedule_weekday', 'rule_weekday_rel', 'rule_id', 'weekday_id', '星期')
    employee_ids = fields.Many2many('hr.employee', 'rule_employee_rel', 'rule_id', 'employee_id', '员工')
    per_count = fields.Integer('每日人数')
    rule = fields.Selection([('1', '交替'), ('2', '连续')], '规则', default='1')
    continuity_days = fields.Integer('连续天数')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    schedule_group_id = fields.Many2one('hrp.schedule_group', '排班分组')

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """过滤不是班次对应的员工"""
        args = args or []
        if 'employees' in self._context:
            # 根据科室过滤班次
            employees = self._context['employees'][0][2] if self._context['employees'] else []
            args += [('id', 'in', employees)]
        return super(HrEmployee, self).name_search(name=name, args=args, operator=operator, limit=limit)

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self._context
        if context.get('order_ticket'):
            if view_type == 'form':
                view = self.env.ref('weixin.sale_order_ticket_form_view')
                if view:
                    view_id = view.id
            elif view_type == 'tree':
                view = self.env.ref('weixin.sale_order_ticket_tree_view')
                if view:
                    view_id = view.id

        return super(HrEmployee, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                      toolbar=toolbar, submenu=submenu)


class HrpScheduleManage(models.Model):
    _name = 'hrp.schedule_manage'
    _description = u'排班管理'

    employee_id = fields.Many2one('hr.employee', '员工')
    start = fields.Datetime('开始时间')
    stop = fields.Datetime('结束时间')
    department_id = fields.Many2one('hr.department', '科室')
    # registered_type_id = fields.Many2one('hrp.registered.type', '号类')
    schedule_type_id = fields.Many2one('hrp.schedule_type', '班次')
    week = fields.Char('周')
    schedule_rule_id = fields.Many2one('hrp.schedule_rule', '班次规则')

    _rec_name = 'employee_id'

    @api.model
    def get_schedule_results(self, edit=False):

        time_now = datetime.now() + timedelta(hours=8)
        calendar = time_now.isocalendar()
        monday = (time_now - timedelta(days=calendar[2] + 1, hours=time_now.hour, minutes=time_now.minute, seconds=time_now.second)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        sunday = (time_now + timedelta(days=7 - calendar[2]) - timedelta(hours=time_now.hour, minutes=time_now.minute, seconds=time_now.second)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        schedule_manages = self.search([('start', '>=', monday), ('stop', '<=', sunday)])

        result = {}
        for s in schedule_manages:
            week = datetime.strptime(s.start, DEFAULT_SERVER_DATETIME_FORMAT).isocalendar()[2]
            employee = (s.employee_id.id, s.employee_id.name)
            if not result.get(employee):
                result.update({employee: {}})
            if not result[employee].get(week):
                result[employee].update({week: []})
            # result[employee][week] = '%s,%s' % (result[employee][week], s.schedule_type_id.name) if result[employee][week] else s.schedule_type_id.name
            result[employee][week].append({'schedule_type_id': s.schedule_type_id.id, 'schedule_type_name': s.schedule_type_id.name, 'color': s.schedule_type_id.color})
        results = []
        for employee, itms in result.items():
            results.append([employee, itms])
        result = {'edit': edit, 'schedule_results': results}
        print 'result:', result
        return result


class HrpScheduleWeekday(models.Model):
    _name = 'hrp.schedule_weekday'
    _description = u'星期'

    name = fields.Char('星期')
    code = fields.Char('编码')
    seq = fields.Integer('顺序')

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """过滤不是班次对应的星期"""
        args = args or []
        if 'weekdays' in self._context:
            # 根据科室过滤班次
            weekdays = self._context['weekdays'][0][2] if self._context['weekdays'] else []
            args += [('id', 'in', weekdays)]
        return super(HrpScheduleWeekday, self).name_search(name=name, args=args, operator=operator, limit=limit)


class HrpScheduleBasic(models.Model):
    _name = 'hrp.schedule_basic'
    _description = u'排班基本规则'

    department_id = fields.Many2one('hr.department', '科室')
    hour_per_day = fields.Float('每日时间小于')
    schedule_type_interval = fields.Float('班次间隔大于')

    _rec_name = 'department_id'


class HrpScheduleGroup(models.Model):
    _name = 'hrp.schedule_group'
    _description = u'人员分组'

    name = fields.Char('名称')
    employee_ids = fields.One2many('hr.employee', 'schedule_group_id', '员工')
