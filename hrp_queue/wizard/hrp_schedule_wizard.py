# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class HrpGenerateSchedule(models.TransientModel):

    _name = 'hrp.generate_schedule'
    _description = u'生成排班'

    @api.multi
    @api.depends('week')
    def _get_date(self):
        time_now = datetime.now()
        for s in self:
            if s.week in ['1', '2', '3']:
                # 按周排
                if s.week == '1':
                    week = 0
                elif s.week == '2':
                    week = 1
                elif s.week == '3':
                    week = 2
                c = time_now.isocalendar()
                first_date = (time_now - timedelta(days=c[2] - 1) + timedelta(days=7 * week)).strftime(
                    DEFAULT_SERVER_DATE_FORMAT)
                end_date = (time_now - timedelta(days=c[2] - 7) + timedelta(days=7 * week)).strftime(
                    DEFAULT_SERVER_DATE_FORMAT)
                week_count = (time_now - timedelta(days=c[2] - 1) + timedelta(days=7 * week)).isocalendar()[1]
            elif s.week in ['4', '5']:
                # 按月排
                if s.week == '4':
                    time_now = datetime(time_now.year, time_now.month, 1)
                elif s.week == '5':
                    if time_now.month + 1 > 12:
                        time_now = datetime(time_now.year + 1, 1, 1)
                    else:
                        time_now = datetime(time_now.year, time_now.month + 1, 1)
                week = 0
                c = time_now.isocalendar()

                first_date = time_now.strftime(DEFAULT_SERVER_DATE_FORMAT)
                if time_now.month + 1 > 12:
                    end_date = (datetime(time_now.year + 1, 1, 1) - timedelta(days=1)).strftime(
                        DEFAULT_SERVER_DATE_FORMAT)
                else:
                    end_date = (datetime(time_now.year, time_now.month + 1, 1) - timedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)

                week_count = (time_now - timedelta(days=c[2] - 1) + timedelta(days=7 * week)).isocalendar()[1]
            else:
                continue

            s.update({
                'first_date': first_date,
                'end_date': end_date,
                'date_text': '%s 至 %s' % (first_date, end_date),
                'week_count': week_count,
            })

    @api.model
    def _get_schedule_types(self):
        if self._context.get('active_id'):
            return self.env['hr.department'].browse(self._context['active_id']).schedule_type_ids.ids
        return False

    week = fields.Selection([('1', '本周'), ('2', '下周')], '时间', default='2') #, ('4', '本月'), ('5', '下月')
    first_date = fields.Date('起始日期', compute=_get_date, store=1)
    end_date = fields.Date('结束日期', compute=_get_date, store=1)
    date_text = fields.Char('日期', compute=_get_date)
    week_count = fields.Char('周', compute=_get_date, store=1)
    schedule_type_ids = fields.Many2many('hrp.schedule_type', 'generate_schedule_type_rel', 'schedule_id', 'type_id', '班次', default=_get_schedule_types)

    @api.multi
    def generate_schedule(self):
        """生成排班"""
        m_department = self.env['hr.department']
        m_schedule_manage = self.env['hrp.schedule_manage']

        def get_schedule_manage_val(tp, week, employee_id, rule):
            """创建排班"""
            # 创建排班
            # 计算日期
            weeks = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5,
                     'sunday': 6}
            start = datetime.strptime(self.first_date, DEFAULT_SERVER_DATE_FORMAT) + \
                    timedelta(days=weeks[week.code], hours=(tp.start - 8))
            stop = datetime.strptime(self.first_date, DEFAULT_SERVER_DATE_FORMAT) + \
                   timedelta(days=weeks[week.code], hours=(tp.stop - 8))
            return {
                'employee_id': employee_id,
                'start': start.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'stop': stop.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'department_id': department.id,
                'schedule_type_id': tp.id,
                'week': self.week_count,
                'schedule_rule_id': rule.id if rule else False,
            }

        def get_employees(tp, week, rule=False, empl_infos=None):
            """获取工时最少的员工"""
            em_count = {}
            # 初始化员工次数
            if rule and rule.employee_ids:
                for em in rule.employee_ids:
                    em_count.update({em.id: 0})
            else:
                for em in tp.employee_ids:
                    em_count.update({em.id: 0})
            # 查询该班次, 该规则排的最少的n个人， n为班次每天人数
            rule_id = rule.id if rule else False
            schedule_manages = m_schedule_manage.search([('schedule_type_id', '=', tp.id), ('schedule_rule_id', '=', rule_id)])
            for s in schedule_manages:
                # 过滤不是该组的人
                if s.employee_id.id not in em_count:
                    continue
                em_count[s.employee_id.id] += 1
            # 累计本次分配的人
            for t, items in schedule_manage_result.items():
                if t.type != tp.type:
                    # 班次类型不同不算
                    continue
                for w, e_infos in items.items():
                    for e_info in e_infos:
                        if e_info['employee_id'] not in em_count:
                            continue
                        em_count[e_info['employee_id']] += 1

            em_items = em_count.items()
            em_items.sort(key=lambda x: x[1])
            # 选中的员工

            per_count = tp.per_count if not rule else rule.per_count
            for em_item in em_items:
                if len(empl_infos) >= per_count:
                    break
                if not em_item:
                    continue
                # 该医生当天是否参与其他班次
                done = False
                for t, items in schedule_manage_result.items():
                    if week in items:
                        for em_info in items[week]:
                            if em_item[0] == em_info['employee_id']:
                                done = True
                                break
                if done:
                    continue

                vacation = False
                # 该医生当天是否休假
                if vacation:
                    continue
                val = get_schedule_manage_val(tp, week, em_item[0], rule)

                # 该员工是否有连续班次
                is_continue = False
                for t, items in schedule_manage_result.items():
                    if t.type == '2':
                        continue
                    for it_week, vals in items.items():
                        for v in vals:
                            if val['employee_id'] == v['employee_id']:
                                if v['start'] <= val['start'] <= v['stop'] or v['start'] <= val['stop'] <= v['stop']:
                                    # 时间有重叠的排班
                                    is_continue = True
                if is_continue:
                    continue
                empl_infos.append(val)

        def update_schedule_result(tp):
            """更新排班结果"""
            # 已存在，返回
            if tp in schedule_manage_result:
                return
            schedule_manage_result.update({tp: {}})
            # 如果该科室本周已排则删除
            m_schedule_manage.search([('department_id', '=', department.id), ('schedule_type_id', '=', tp.id),
                                      ('week', '=', self.week_count)]).unlink()
            # 星期
            for week in tp.weekday_ids:
                # 该星期已排
                if week in schedule_manage_result[tp]:
                    continue
                # 遍历规则,找到该天的规则
                r = None
                for rule in tp.rule_ids:
                    if week in rule.weekday_ids:
                        r = rule
                        break
                empl_infos = []
                if r:
                    # 根据规则选人
                    get_employees(tp, week, r, empl_infos=empl_infos)
                    if r.rule == '2':
                        # 连续排班，取连续次数
                        continuity_days = r.continuity_days
                        for wk in r.weekday_ids:
                            # 该星期已排，跳过
                            if wk in schedule_manage_result[tp]:
                                continue
                            # 超过连续天数
                            if continuity_days < 1:
                                break
                            # 选取同样人排入其他日期
                            empl_infos2 = []
                            for empl_info in empl_infos:
                                # 获取结果
                                val = get_schedule_manage_val(tp, wk, empl_info['employee_id'], r)
                                empl_infos2.append(val)
                            schedule_manage_result[tp].update({wk: empl_infos2})
                            continuity_days -= 1
                else:
                    # 默认排班，取工时最少的人
                    get_employees(tp, week, empl_infos=empl_infos)
                # 加入排班序列
                schedule_manage_result[tp].update({week: empl_infos})

        department = m_department.search([('id', '=', self._context['active_id'])])
        if not department:
            raise UserError(_('科室为空'))

        # 本次排班结果
        schedule_manage_result = {}

        # 先排非工作
        # 班次
        for tp in self.schedule_type_ids:
            if tp.type != '2':
                continue
            update_schedule_result(tp)
        # 正常上班
        for tp in self.schedule_type_ids:
            update_schedule_result(tp)
        # 创建排班
        for tp, item in schedule_manage_result.items():
            for wk, vals in item.items():
                # 当天选中的员工
                # create_schedule_manage(tp, wk, vals)
                for val in vals:
                    m_schedule_manage.create(val)

        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('hrp_queue.hrp_schedule_manage_action')
        calendar_view_id = imd.xmlid_to_res_id('hrp_queue.view_hrp_schedule_manage_calendar')
        tree_view_id = imd.xmlid_to_res_id('hrp_queue.view_hrp_schedule_manage_tree')
        form_view_id = imd.xmlid_to_res_id('hrp_queue.view_hrp_schedule_manage_form')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[calendar_view_id, 'calendar'], [tree_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }

        result.update({'domain': "[('department_id', '=', %s)]" % department.id})
        return result
