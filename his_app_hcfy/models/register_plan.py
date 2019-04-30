# -*- encoding:utf-8 -*-
from datetime import datetime, timedelta
import time
from odoo import api
from odoo import fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT



class RegisterPlan(models.Model):
    _name = 'his.register_plan'
    _description = '队列计划'

    medical_date = fields.Date('就诊日期')
    department_id = fields.Many2one('hr.department', '科室')
    employee_id = fields.Many2one('hr.employee', '医生')
    line_ids = fields.One2many('his.register_plan_line', 'register_plan_id', '就诊记录明细')
    schedule_id = fields.Many2one('his.work_schedule', '安排', ondelete='cascade')


    @api.model
    def generate_register_plan(self):
        """根据号源表和预约有效天数产生挂号计划表"""

        # # 在每天0点运行该计划
        # hour = (datetime.now() + timedelta(hours=8)).hour
        # if hour != 0:
        #     return

        work_schedule_obj = self.env['his.work_schedule'] # 挂号安排
        register_plan_line_obj = self.env['his.register_plan_line']
        department_obj = self.env['hr.department']
        clinic_item_category_obj = self.env['his.clinic_item_category']
        schedule_shift_obj = self.env['his.schedule_shift']
        register_source_obj = self.env['his.register_source']

        appoint_day = self.env.user.company_id.appoint_day # 预约有效天数

        today = datetime.strptime(datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT), DEFAULT_SERVER_DATE_FORMAT) # 当前日期

        last_day = today + timedelta(days=appoint_day)

        for work_schedule in work_schedule_obj.search([('date', '>=', today.strftime(DEFAULT_SERVER_DATE_FORMAT)), ('date', '<=', last_day.strftime(DEFAULT_SERVER_DATE_FORMAT)), ('is_generate_register_plan', '=', False), ('is_outpatient', '=', True)]):
            # 把工作计划的班次按科室分组
            departments = {}
            for shift in work_schedule.shifts:
                departments.setdefault(shift.department_id, []).append(shift)

            for department in departments:
                # 创建挂号计划主记录
                register_plan = self.create({
                    'medical_date': work_schedule.date,
                    'department_id': department.id,
                    'employee_id': work_schedule.employee_id.id,
                    'schedule_id': work_schedule.id
                })
                medical_sort = 1 # 预约序号
                shifts = sorted(departments[department], key=lambda x: x.start_time) # 班次
                for shift in shifts:
                    for register_source in shift.register_source_ids:

                        register_plan_line_obj.create({
                            'register_plan_id': register_plan.id,
                            'medical_sort': medical_sort,
                            'shift_type_id': shift.shift_type_id.id,
                            'time_point_name': register_source.time_point_name,
                        })

                        medical_sort += 1

            work_schedule.is_generate_register_plan = True

        # # 下周一的日期
        # today = datetime.strptime(datetime.today().strftime(DEFAULT_SERVER_DATE_FORMAT), DEFAULT_SERVER_DATE_FORMAT)
        # week = int(today.strftime('%w'))
        # next_week = today + timedelta(days=7 - week + 1)

        # 科室排班生成计划
        for department in department_obj.search([('is_shift', '=', True), ('is_outpatient', '=', False)]):
            clinic_item_category = clinic_item_category_obj.search([('department_id', '=', department.id)])
            if clinic_item_category:
                date = today + timedelta(days=clinic_item_category.max_days)
                date_str = date.strftime(DEFAULT_SERVER_DATE_FORMAT)
                if work_schedule_obj.search([('department_id', '=', department.id), ('is_outpatient', '=', False), ('date', '=', date_str)]):
                    continue

                work_schedule = work_schedule_obj.create({
                    'department_id': department.id,
                    'date': date_str,
                    'is_generate_register_plan': True,
                    'is_outpatient': False
                })
                week = date.strftime('%w')
                shifts = [shift for shift in department.shift_type_ids if shift.week_name == week]
                schedule_shifts = []
                for shift_type in shifts:
                    schedule_shift = schedule_shift_obj.create({
                        'department_id': department.id,
                        'employee_id': False,
                        'schedule_id': work_schedule.id,
                        'shift_type_id': shift_type.id,
                        'start_time': shift_type.start_time,
                        'end_time': shift_type.end_time,
                        'register_time_interval': False,
                        'limit': shift_type.max_execute_count
                    })
                    schedule_shifts.append(schedule_shift)
                    # 自动生成号源
                    start = date + timedelta(hours=shift_type.start_time)
                    end = date + timedelta(hours=shift_type.end_time)
                    minute_interval = (
                                      shift_type.end_time * 60 - shift_type.start_time * 60) / shift_type.max_execute_count
                    count = 1
                    while start < end:
                        register_source_obj.create({
                            'shift_id': schedule_shift.id,
                            'time_point_name': start.strftime('%H:%M'),
                            'department_id': department.id,
                            'employee_id': False,
                            'date': date_str,
                            'shift_type_id': shift_type.id
                        })
                        start += timedelta(minutes=int(minute_interval))
                        if count >= shift_type.max_execute_count:
                            break
                        count += 1

                # 生成预约计划表
                # 创建挂号计划主记录
                register_plan = self.create({
                    'medical_date': work_schedule.date,
                    'department_id': department.id,
                    'schedule_id': work_schedule.id
                })
                medical_sort = 1  # 预约序号
                for shift in schedule_shifts:
                    for register_source in shift.register_source_ids:
                        register_plan_line_obj.create({
                            'register_plan_id': register_plan.id,
                            'medical_sort': medical_sort,
                            'shift_type_id': shift.shift_type_id.id,
                            'time_point_name': register_source.time_point_name,
                        })
                        medical_sort += 1


            else:
                # 产生近一周的排班
                for i in range(7):
                    # date = next_week + timedelta(days=i)
                    date = today + timedelta(days=i)
                    date_str = date.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    if work_schedule_obj.search([('department_id', '=', department.id), ('is_outpatient', '=', False), ('date', '=', date_str)]):
                        continue

                    work_schedule = work_schedule_obj.create({
                        'department_id': department.id,
                        'date': date_str,
                        'is_generate_register_plan': True,
                        'is_outpatient': False
                    })
                    week = date.strftime('%w')
                    shifts = [shift for shift in department.shift_type_ids if shift.week_name == week]
                    if not shifts:
                        shifts = [shift for shift in department.shift_type_ids if not shift.week_name]


                    schedule_shifts = []
                    for shift_type in shifts:
                        if not shift_type.max_execute_count:
                            continue

                        schedule_shift = schedule_shift_obj.create({
                            'department_id': department.id,
                            'employee_id': False,
                            'schedule_id': work_schedule.id,
                            'shift_type_id': shift_type.id,
                            'start_time': shift_type.start_time,
                            'end_time': shift_type.end_time,
                            'register_time_interval': False,
                            'limit': shift_type.max_execute_count
                        })
                        schedule_shifts.append(schedule_shift)
                        # 自动生成号源
                        start = date + timedelta(hours=shift_type.start_time)
                        end = date + timedelta(hours=shift_type.end_time)
                        minute_interval = (shift_type.end_time * 60 - shift_type.start_time * 60) / shift_type.max_execute_count
                        count = 1
                        overage = 0
                        while start < end:
                            register_source_obj.create({
                                'shift_id': schedule_shift.id,
                                'time_point_name': start.strftime('%H:%M'),
                                'department_id': department.id,
                                'employee_id': False,
                                'date': date_str,
                                'shift_type_id': shift_type.id
                            })
                            minutes, overage = divmod(minute_interval + overage, 1)
                            start += timedelta(minutes=minutes)
                            if count >= shift_type.max_execute_count:
                                break
                            count += 1
                            time.sleep(1)


                    # 生成预约计划表
                    # 创建挂号计划主记录
                    register_plan = self.create({
                        'medical_date': work_schedule.date,
                        'department_id': department.id,
                        'schedule_id': work_schedule.id
                    })
                    medical_sort = 1 # 预约序号
                    for shift in schedule_shifts:
                        for register_source in shift.register_source_ids:
                            register_plan_line_obj.create({
                                'register_plan_id': register_plan.id,
                                'medical_sort': medical_sort,
                                'shift_type_id': shift.shift_type_id.id,
                                'time_point_name': register_source.time_point_name,
                            })
                            medical_sort += 1



class RegisterPlanLine(models.Model):
    _name = 'his.register_plan_line'
    _description = '挂号计划表明细'
    _order = 'id asc'

    register_plan_id = fields.Many2one('his.register_plan', '挂号计划', ondelete='cascade')
    medical_sort = fields.Integer('预约序号')
    shift_type_id = fields.Many2one('his.shift_type', '班次')
    time_point_name = fields.Char('时间点')
    partner_id = fields.Many2one('res.partner', '患者')
    source = fields.Selection([('manual', '人工挂号'), ('app', 'APP')], '来源')
    register_time = fields.Datetime('预约/挂号时间')
    reserve_time_point_name = fields.Char('预约时间点')
    register_id = fields.Many2one('his.register', 'HIS挂号记录')
    state = fields.Selection([], '状态')



