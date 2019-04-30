# -*- encoding:utf-8 -*-
from datetime import datetime, timedelta

from odoo import api
from odoo import fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from odoo.exceptions import Warning


class WorkSchedule(models.Model):
    _name = 'his.work_schedule'
    _description = '工作计划'
    update_external = True  # 更新外部服务器数据

    department_id = fields.Many2one('hr.department', '科室')
    employee_id = fields.Many2one('hr.employee', '医生')
    date = fields.Date('日期')
    shifts = fields.One2many('his.schedule_shift', 'schedule_id', '班次')
    limit = fields.Integer('限号数')
    is_generate_register_plan = fields.Boolean('已生成队列计划')
    is_outpatient = fields.Boolean('是门诊计划', default=True)


    @api.model
    def get_work_schedule_info(self):
        departments = self.env['hr.department'].search([('is_shift', '=', True), ('is_outpatient', '=', True)])
        return [{'id': department.id, 'name': department.name} for department in departments]


    @api.model
    def change_work_schedule(self, *_, **kwargs):
        """排班

        @param kwargs: 格式：
            纯添加：
            let mm = {
                'schedule': [
                    {
                        'empl_name': '补吉斯',
                        'days': [
                            {
                                'date': '2017-04-24',
                                'empl_id': 7309,
                                'expired': True,
                                'shifts': []
                            },
                            {
                                'date': '2017-04-25',
                                'empl_id': 7309,
                                'expired': True,
                                'shifts': []
                            },
                            {
                                'date': '2017-04-26',
                                'empl_id': 7309,
                                'expired': True,
                                'shifts': []
                            },
                            {
                                'date': '2017-04-27',
                                'empl_id': 7309,
                                'expired': True,
                                'shifts': []
                            },
                            {
                                'date': '2017-04-28',
                                'empl_id': 7309,
                                'expired': True,
                                'shifts': [
                                    {
                                        'shift_id': 308,
                                        'start_time': 8,
                                        'shift_color': '#3E2BEE',
                                        'shift_name': '上',
                                        'id': 711,
                                        'department_id': 1774
                                    }
                                ]
                            },
                            {
                                'date': '2017-04-29',
                                'empl_id': 7309,
                                'expired': False,
                                'shifts': [
                                    {
                                        'shift_name': '上',
                                        'start_time': 8,
                                        'shift_id': 308,
                                        'shift_color': '#3E2BEE'
                                    },
                                    {
                                        'shift_name': '下',
                                        'start_time': 14,
                                        'shift_id': 309,
                                        'shift_color': '#7EEE1D'
                                    }
                                ]
                            },
                            {
                                'date': '2017-04-30',
                                'empl_id': 7309,
                                'expired': False,
                                'shifts': [
                                    {
                                        'shift_name': '上',
                                        'start_time': 8,
                                        'shift_id': 308,
                                        'shift_color': '#3E2BEE'
                                    },
                                    {
                                        'shift_name': '下',
                                        'start_time': 14,
                                        'shift_id': 309,
                                        'shift_color': '#7EEE1D'
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'empl_name': '陈佳',
                        'days': [
                            {
                                'date': '2017-04-24',
                                'empl_id': 7141,
                                'expired': True,
                                'shifts': []
                            },
                            {
                                'date': '2017-04-25',
                                'empl_id': 7141,
                                'expired': True,
                                'shifts': []
                            },
                            {
                                'date': '2017-04-26',
                                'empl_id': 7141,
                                'expired': True,
                                'shifts': []
                            },
                            {
                                'date': '2017-04-27',
                                'empl_id': 7141,
                                'expired': True,
                                'shifts': []
                            },
                            {
                                'date': '2017-04-28',
                                'empl_id': 7141,
                                'expired': True,
                                'shifts': []
                            },
                            {
                                'date': '2017-04-29',
                                'empl_id': 7141,
                                'expired': False,
                                'shifts': [
                                    {
                                        'shift_name': '上',
                                        'start_time': 8,
                                        'shift_id': 308,
                                        'shift_color': '#3E2BEE'
                                    },
                                    {
                                        'shift_name': '下',
                                        'start_time': 14,
                                        'shift_id': 309,
                                        'shift_color': '#7EEE1D'
                                    }
                                ]
                            },
                            {
                                'date': '2017-04-30',
                                'empl_id': 7141,
                                'expired': False,
                                'shifts': [
                                    {
                                        'shift_name': '上',
                                        'start_time': 8,
                                        'shift_id': 308,
                                        'shift_color': '#3E2BEE'
                                    },
                                    {
                                        'shift_name': '下',
                                        'start_time': 14,
                                        'shift_id': 309,
                                        'shift_color': '#7EEE1D'
                                    }
                                ]
                            }
                        ]
                    }
                ],
                'department_id': 1774
            };
            修改：
                let mm = {
                    'schedule': [
                        {
                            'empl_name': '补吉斯',
                            'days': [
                                {
                                    'date': '2017-04-24',
                                    'empl_id': 7309,
                                    'expired': true,
                                    'shifts': []
                                },
                                {
                                    'date': '2017-04-25',
                                    'empl_id': 7309,
                                    'expired': true,
                                    'shifts': []
                                },
                                {
                                    'date': '2017-04-26',
                                    'empl_id': 7309,
                                    'expired': true,
                                    'shifts': []
                                },
                                {
                                    'date': '2017-04-27',
                                    'empl_id': 7309,
                                    'expired': true,
                                    'shifts': []
                                },
                                {
                                    'date': '2017-04-28',
                                    'empl_id': 7309,
                                    'expired': true,
                                    'shifts': [
                                        {
                                            'shift_id': 308,
                                            'start_time': 8,
                                            'shift_color': '#3E2BEE',
                                            'shift_name': '上',
                                            'id': 711,
                                            'department_id': 1774
                                        }
                                    ]
                                },
                                {
                                    'date': '2017-04-29',
                                    'empl_id': 7309,
                                    'expired': false,
                                    'shifts': [
                                        {
                                            'shift_id': 308,
                                            'start_time': 8,
                                            'shift_color': '#3E2BEE',
                                            'shift_name': '上',
                                            'id': 720,
                                            'department_id': 1774
                                        },
                                        {
                                            'shift_id': 309,
                                            'deleted': true,
                                            'start_time': 14,
                                            'shift_color': '#7EEE1D',
                                            'shift_name': '下',
                                            'id': 721,
                                            'department_id': 1774
                                        }
                                    ]
                                },
                                {
                                    'date': '2017-04-30',
                                    'empl_id': 7309,
                                    'expired': false,
                                    'shifts': [
                                        {
                                            'shift_id': 308,
                                            'start_time': 8,
                                            'shift_color': '#3E2BEE',
                                            'shift_name': '上',
                                            'id': 722,
                                            'department_id': 1774
                                        },
                                        {
                                            'shift_id': 309,
                                            'start_time': 14,
                                            'shift_color': '#7EEE1D',
                                            'shift_name': '下',
                                            'id': 723,
                                            'department_id': 1774
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            'empl_name': '陈佳',
                            'days': [
                                {
                                    'date': '2017-04-24',
                                    'empl_id': 7141,
                                    'expired': true,
                                    'shifts': []
                                },
                                {
                                    'date': '2017-04-25',
                                    'empl_id': 7141,
                                    'expired': true,
                                    'shifts': []
                                },
                                {
                                    'date': '2017-04-26',
                                    'empl_id': 7141,
                                    'expired': true,
                                    'shifts': []
                                },
                                {
                                    'date': '2017-04-27',
                                    'empl_id': 7141,
                                    'expired': true,
                                    'shifts': []
                                },
                                {
                                    'date': '2017-04-28',
                                    'empl_id': 7141,
                                    'expired': true,
                                    'shifts': []
                                },
                                {
                                    'date': '2017-04-29',
                                    'empl_id': 7141,
                                    'expired': false,
                                    'shifts': [
                                        {
                                            'shift_id': 308,
                                            'start_time': 8,
                                            'shift_color': '#3E2BEE',
                                            'shift_name': '上',
                                            'id': 724,
                                            'department_id': 1774
                                        },
                                        {
                                            'shift_id': 309,
                                            'start_time': 14,
                                            'shift_color': '#7EEE1D',
                                            'shift_name': '下',
                                            'id': 725,
                                            'department_id': 1774
                                        }
                                    ]
                                },
                                {
                                    'date': '2017-04-30',
                                    'empl_id': 7141,
                                    'expired': false,
                                    'shifts': [
                                        {
                                            'shift_id': 308,
                                            'start_time': 8,
                                            'shift_color': '#3E2BEE',
                                            'shift_name': '上',
                                            'id': 726,
                                            'department_id': 1774
                                        },
                                        {
                                            'shift_id': 309,
                                            'start_time': 14,
                                            'shift_color': '#7EEE1D',
                                            'shift_name': '下',
                                            'id': 727,
                                            'department_id': 1774
                                        }
                                    ]
                                }
                            ]
                        }
                    ],
                    'department_id': 1774
                };


        """
        # employee_obj = self.env['hr.employee']
        schedule_shift_obj = self.env['his.schedule_shift'] # 排班班次
        shift_type_obj = self.env['his.shift_type'] # 科室班次
        register_source_obj = self.env['his.register_source'] # 号源
        schedule_department_employee_obj = self.env['his.schedule_department_employee'] # 科室人员安排
        employee_register_limit_obj = self.env['his.employee_register_limit'] # 限号设置

        today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)

        department_id = kwargs['department_id']

        for schedule in kwargs['schedule']:

            for day in schedule['days']:
                if day['expired']: # 已过期
                    continue

                employee_id = day['empl_id'] # 医生
                date = day['date'] # 排班日期

                work_schedule = self.search([('department_id', '=', department_id), ('employee_id', '=', employee_id), ('date', '=', date)]) # 排班计划

                if not day['shifts']: # 没有班次
                    if work_schedule:
                        work_schedule.unlink()
                    continue


                all_shift_deleted = True # 是否删除计划的所有班次
                for shift in day['shifts']:
                    if shift.get('deleted'):
                        schedule_shift_obj.browse(shift['id']).unlink()
                    else:
                        all_shift_deleted = False

                if all_shift_deleted:
                    work_schedule.unlink()
                    continue

                if not work_schedule:
                    work_schedule = self.create({
                        'department_id': department_id, # 科室
                        'employee_id': employee_id, # 医生
                        'date': date, # 排班日期
                        'is_outpatient': True, # 是门诊计划
                    })


                schedule_department_employee = schedule_department_employee_obj.search([('department_id', '=', department_id), ('employee_id', '=', employee_id)])
                register_time_interval = schedule_department_employee.register_time_interval  # 挂号间隔

                # 限号设置
                register_limit = employee_register_limit_obj.search([('schedule_department_employee_id', '=', schedule_department_employee.id), ('limit_type', '=', 'all')])
                day_max = 0 # 全天最大挂号数量
                for limit in register_limit:
                    if limit.limit_type == 'all':
                        if limit.limit > day_max:
                            day_max = limit.limit

                day_total_count = 0
                for shift in day['shifts']:
                    if shift.get('id'): # 排班班次已经存在
                        continue

                    # 超过限号数
                    if day_max:
                        if day_total_count >= day_max:
                            break

                    shift_type_id = shift['shift_id'] # 科室班次
                    shift_type = shift_type_obj.browse(shift_type_id) # 科室班次
                    start_time = shift_type.start_time # 上班时间
                    end_time = shift_type.end_time # 下班时间

                    # 创建计划排班班次
                    schedule_shift = schedule_shift_obj.create({
                        'employee_id': employee_id, # 医生
                        'department_id': department_id, # 科室
                        'schedule_id': work_schedule.id, # 排班计划
                        'shift_type_id': shift_type_id, # 科室班次
                        'start_time': start_time, # 上班时间
                        'end_time': end_time, # 下班时间
                        'register_time_interval': register_time_interval, # 挂号间隔
                        # 'date': work_schedule.date
                    })

                    shift_max = 0 # 班次限号
                    register_limit = employee_register_limit_obj.search([('schedule_department_employee_id', '=', schedule_department_employee.id), ('limit_type', '=', 'shift'), ('shift_type_id', '=', shift_type_id)])
                    if register_limit:
                        shift_max = register_limit.limit

                    # 自动生成号源
                    start = today + timedelta(hours=start_time)
                    end = today + timedelta(hours=end_time)
                    time_interval = register_time_interval.split(',')
                    count = 0
                    while start < end:
                        _, remainder = divmod(count, len(time_interval))
                        register_source_obj.create({
                            'shift_id': schedule_shift.id,
                            'time_point_name': start.strftime('%H:%M')
                        })
                        start += timedelta(minutes=int(time_interval[remainder]))
                        count += 1
                        day_total_count += 1
                        if day_max:
                            if day_total_count >= day_max:
                                break

                        if shift_max:
                            if count >= shift_max:
                                break




    @api.model
    def get_work_schedule(self, *_, **kwargs):
        shift_type_obj = self.env['his.shift_type']
        department_obj = self.env['hr.department']

        department_id = kwargs['department_id']

        start_date = datetime.strptime(kwargs['start_date'], DATE_FORMAT)
        end_date = datetime.strptime(kwargs['end_date'], DATE_FORMAT)
        days = (end_date - start_date).days + 1

        now = datetime.now() # 当前时间

        # 科室班次
        department_shift_type = shift_type_obj.search([('department_id', '=', department_id)])
        # 最晚上班时间
        dept_last_work_time = 0
        for shift_type in department_shift_type:
            if shift_type.start_time > dept_last_work_time:
                dept_last_work_time = shift_type.start_time


        # work_schedule = [{'empl_id': 125, 'empl_name': '张三', 'title': '主任医士', 'shift': [{'shift_id': 1, 'shift_name': '上午', 'date': '2016-12-25', 'expired': '是否过期'}]}]

        work_schedule = []
        for department_employee in department_obj.browse(department_id).employees:
            employee = department_employee.employee_id
            employee_days = []
            for i in range(days):
                day = start_date + timedelta(days=i)
                # 是否过期
                if day.strftime(DATE_FORMAT) == now.strftime(DATE_FORMAT):  # 当天
                    if dept_last_work_time:
                        if now >= datetime.strptime(now.strftime(DATE_FORMAT), DATE_FORMAT) + timedelta(hours=dept_last_work_time):
                            expired = True
                        else:
                            expired = False
                    else:
                        expired = False
                else:
                    if day < now:
                        expired = True
                    else:
                        expired = False

                schedule = self.search([('employee_id', '=', employee.id), ('date', '=', day), ('department_id', '=', department_id)])
                if schedule:

                    shifts = [
                        {
                            'id': schedule_shift.id,
                            'shift_id': schedule_shift.shift_type_id.id,
                            'start_time': schedule_shift.shift_type_id.start_time,
                            'shift_name': schedule_shift.shift_type_id.label if schedule_shift.department_id.id == department_id else u'%s(%s)' % (schedule_shift.shift_type_id.label, schedule_shift.department_id.name),
                            'shift_color': schedule_shift.shift_type_id.color if schedule_shift.department_id.id == department_id else '#EEEEEE',
                            'department_id': schedule_shift.department_id.id,
                        } for schedule_shift in schedule.shifts]

                    shifts = sorted(shifts, key=lambda x: x['start_time'])

                    employee_days.append({
                        'empl_id': employee.id,
                        'date': day.strftime(DATE_FORMAT),
                        'expired': expired,
                        'shifts': shifts
                    })
                else:
                    employee_days.append({
                        'empl_id': employee.id,
                        'date': day.strftime(DATE_FORMAT),
                        'expired': expired,
                        'shifts': []
                    })

            work_schedule.append({
                'empl_name': employee.name,
                'days': employee_days
            })


        week_label = ['一', '二', '三', '四', '五', '六', '日']
        week = []
        dates = []
        for i in range(days):
            day = start_date + timedelta(days=i)
            dates.append({'label': day.strftime('%m-%d'), 'value': day.strftime(DATE_FORMAT)})
            week.append(week_label[day.weekday()])

        result = {
            'shift_type': [{'id': shift_type.id, 'start_time': shift_type.start_time, 'color': shift_type.color, 'name': shift_type.label, 'type': shift_type.type}for shift_type in department_shift_type], # 科室班次
            'work_schedule': work_schedule,
            'dates': dates,
            'week': week,
            'days': days
        }
        return result

    @api.multi
    def unlink(self):
        # today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT) # 当前日期


        for schedule_shift in self.shifts:
            for register_source in schedule_shift.register_source_ids:
                if register_source.state == '1':
                    raise Warning('排班已经有人挂号，不能删除，请停诊')

        return super(WorkSchedule, self).unlink()
