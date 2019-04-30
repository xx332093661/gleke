# -*- encoding:utf-8 -*-
import importlib
import logging
import traceback
from datetime import datetime, timedelta

from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

_logger = logging.getLogger(__name__)

module = {}


class SyncRegister(models.Model):
    _inherit = 'his.sync_define'


    def register_poll(self, result, sync):
        """挂号轮询回调"""
        def create_partner():
            """创建病人"""
            birth_date = res['birth_date']
            if birth_date:
                birth_date = birth_date.split()[0]
            return partner_obj.create_partner({
                'his_id': res['partner_his_id'],  # HISID
                'outpatient_num': res['outpatient_num'],  # 门诊号
                'name': res['name'],  # 姓名
                'sex': res['sex'],  # 性别
                'gender': 'male' if res['sex'] == u'男' or res['sex'] == '男' else 'female',  # 性别
                'id_no': res['id_no'],  # 身份证号
                'card_no': res['card_no'],  # 就诊卡号
                'medical_no': res['medical_no'],  # 医保卡号
                'is_patient': True,  # 是患者,
                'birth_date': birth_date
            })

        def query_reserve_record():
            """查询预约记录"""
            return reserve_record_obj.search([('reserve_date', '=', register_date), ('receipt_no', '=', res['receipt_no'])])

        def create_register():
            """创建挂号记录"""
            register_res = register_obj.his_id_exist(res['his_id'])
            if register_res:
                return register_res

            register_res = register_obj.create({
                'his_id': res['his_id'],  # HISID
                'receipt_no': res['receipt_no'],  # NO(单据号)
                'record_state': res['record_state'],  # 记录状态
                'exe_state': res['exe_state'],  # 执行状态
                'register_type': res['register_type'],  # 号类名称
                'employee_id': employee_id,  # 医生
                'department_id': department_id,  # 科室
                # 'is_emerg_treat': res['is_emerg_treat'],  # 是否急诊
                # 'fee_name': res['fee_name'],  # 收费项目名称
                'register_datetime': res['register_datetime'],  # 登记时间
                'register_date': register_date,  # 登记日期
                'partner_id': partner.id,  # 病人,
                'operator_code': operator_code, # 操作员编号
            })

            return register_res

        def create_register_treatment_process():
            """挂号就医流程"""
            if res['record_state'] == 3: # 退号
                return

            if res['record_state'] == 2: # 退号
                return

            # 有预约记录的，不用创建
            if reserve_record:
                line = treatment_process_line_obj.search([('reserve_id', '=', reserve_record.id)])
                if line:
                    if not line.receipt_no:
                        line.receipt_no = res['receipt_no']
                return

            if register.total_queue_id: # 重复处理
                return

            if res['exe_state'] != 0: # 已执行, 不做处理
                return

            # 手动完成以前还没有完成的就医流程
            treatment_process_obj.search([('partner_id', '=', partner.id), ('state', '=', 'doing'), ('visit_date', '<', today)]).write({
                'state': 'done'
            })

            treatment_process = treatment_process_obj.search([('visit_date', '=', today), ('partner_id', '=', partner.id), ('state', '=', 'doing')])
            if not treatment_process:
                treatment_process = treatment_process_obj.create({
                    'partner_id': partner.id,
                    'visit_date': today,
                    'state': 'doing'
                })

            # 重复处理
            if treatment_process_line_obj.search([('process_id', '=', treatment_process.id), ('receipt_no', '=', res['receipt_no'])]):
                return


            empl_id = employee_id
            if reserve_record:
                empl_id = reserve_record.employee_id.id

            return treatment_process_line_obj.create({
                'process_id': treatment_process.id,
                'name': '挂号',
                'business': '挂号',  # 业务类型
                'code': '01',
                'department_id': department_id,
                'employee_id': empl_id,
                'location': department_obj.browse(department_id).location or '',
                'update_time': datetime.now().strftime(DATETIME_FORMAT),
                'process_type': '2', # 流程类型 '1', '排队'  '2', '不排队'
                'state': 'done',
                'receipt_no': res['receipt_no'], # 挂号单号
            })

        def create_queue():
            """创建队列"""
            if res['record_state'] == 3: # 退号
                return

            if res['record_state'] == 2: # 退号
                register1 = register_obj.search([('receipt_no', '=', res['receipt_no']), ('partner_id', '=', partner.id), ('record_state', '=', 1)])
                if register1:
                    if register1.record_state != 3:  # 退费
                        register1.record_state = 3

                    total_queue = register1.total_queue_id
                    if total_queue:
                        if total_queue.state != '1':
                            total_queue.state = '1'  # 退号


                return

            if res['exe_state'] != 0: # 已执行, 不做处理
                return

            if register.total_queue_id: # 重复处理
                return

            # 就诊业务的执行科室超过两级，取第二级
            dept_id = register.department_id.id
            if dept_id:
                id_tree = [dept_id]
                dept = department_obj.browse(dept_id)
                while dept.parent_id:
                    id_tree.insert(0, dept.parent_id.id)
                    dept = dept.parent_id

                id_tree = id_tree[:2]
                dept_id = id_tree[-1]

            vals = {
                'outpatient_num': partner.outpatient_num,  # 门诊号
                'partner_id': partner.id,
                'business': '就诊',  # 业务类型
                'department_id': dept_id,
                # 'room_id': False,  # 挂号诊室
                'employee_id': register.employee_id.id,
                'register_type': res['register_type'], # 号类
                'part': False,  # 部位
                'coll_method': False,  # 采集方式
                # 'is_emerg_treat': res['is_emerg_treat'],  # 是否急诊
                'origin': '1',  # 病人来源 1-门诊 2-住院
                'enqueue_datetime': fields.Datetime.now(),  # 入队时间
                'state': None,

                'origin_table': 'register',  # 来源表
                'origin_id': register.id,  # 对应来源表的ID,
                'operator_code': res['operator_code'], # 操作员编号
            }

            register_source_res = None
            if reserve_record:
                register_plan = register_plan_obj.search([('medical_date', '=', register_date), ('department_id', '=', reserve_record.department_id.id), ('employee_id', '=', reserve_record.employee_id.id)]) # 队列计划

                time_point_name = reserve_record.register_source_id.time_point_name # 预约记录的号源的时间点
                line = register_plan_line_obj.search([('register_plan_id', '=', register_plan.id),  ('partner_id', '=', partner.id), ('time_point_name', '=', time_point_name)])
                if line:
                    line.register_id = register.id
                    vals.update({
                        'appointment_number': line.medical_sort,  # 预约顺序号,
                        'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 预约时间
                        'employee_id': reserve_record.employee_id.id,
                        'origin': '6',  # 病人来源 1-门诊 2-住院 6-APP
                    })
            else:
                if department.name.find(u'急诊') == -1:
                    if employee_id:
                        _logger.info(u'有挂号医生')
                        _logger.info(u'当前时间:%s', current_time)
                        try:
                            # 科室对应的班次
                            shift_type = shift_type_obj.search([('department_id', '=', dept_id)])
                            if shift_type:
                                shifts = sorted(shift_type, key=lambda x: x.start_time)  # 班次

                                first_shift_start_time = today + timedelta(hours=shifts[0].start_time)  # 上午的上班时间
                                _logger.info(u'上午上班时间:%s', first_shift_start_time)
                                first_shift_end_time = today + timedelta(hours=shifts[0].end_time)  # 上午的下班时间
                                _logger.info(u'上午下班时间:%s', first_shift_end_time)
                                last_shift_start_time = today + timedelta(hours=shifts[-1].start_time)  # 下午的上班时间
                                _logger.info(u'下午上班时间:%s', last_shift_start_time)
                                last_shift_end_time = today + timedelta(hours=shifts[-1].end_time)  # 下午的下班时间
                                _logger.info(u'下午下班时间:%s', last_shift_end_time)

                                register_plan = register_plan_obj.search([('medical_date', '=', register_date), ('department_id', '=', dept_id), ('employee_id', '=', employee_id)])  # 队列计划

                                _logger.info(u'队列计划ID:%d', register_plan.id)

                                # 计算当前时间对应科室的班次
                                #    上班前              上午                 休息              下午               下班后
                                # ____________|__________________________|__________|__________________________|____________

                                # ####上班前####
                                if current_time < first_shift_start_time:
                                    _logger.info(u'上班前')
                                    shift_type_id = shifts[0].id # 科室班次
                                    _logger.info(u'当前班次ID:%d', shift_type_id)
                                    register_plan_lines = register_plan_line_obj.search([('register_plan_id', '=', register_plan.id), ('shift_type_id', '=', shift_type_id), ('partner_id', '=', False)], order='id asc')
                                    for line in register_plan_lines:
                                        _logger.info(u'队列计划明细ID:%d', line.id)
                                        # if line.shift_type_id.id != shift_type_id:
                                        #     continue
                                        # if line.partner_id:
                                        #     continue

                                        time_point_name = line.time_point_name  # 号源的时间点
                                        register_source = register_source_obj.search([('date', '=', register_date), ('department_id', '=', dept_id), ('employee_id', '=', employee_id), ('time_point_name', '=', time_point_name)])
                                        _logger.info(u'队列计划明细对应号源ID:%s', register_source.id)
                                        if not register_source:
                                            continue
                                        _logger.info(u'队列计划明细对应号源状态:%s', register_source.state)
                                        if register_source.state != '0':
                                            continue

                                        try:
                                            register_source_obj.appointment_register(register_source.id) # 号源占用
                                            register_source_res = register_source.id
                                            line.write({
                                                'source': 'manual',
                                                'partner_id': partner.id,
                                                'register_time': register_datetime_str,
                                                'register_id': register.id,
                                            })
                                            vals.update({
                                                'appointment_number': line.medical_sort,  # 预约顺序号,
                                                'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 预约时间
                                            })
                                            break
                                        except:
                                            _logger.error(u'有挂号医生，修改队列计划明细出错')
                                            _logger.error(traceback.format_exc())
                                            continue
                                # ####上午####
                                elif first_shift_start_time <= current_time <= first_shift_end_time:
                                    _logger.info(u'上午')
                                    shift_type_id = shifts[0].id # 科室班次
                                    _logger.info(u'当前班次ID:%d', shift_type_id)
                                    register_plan_lines = register_plan_line_obj.search([('register_plan_id', '=', register_plan.id), ('shift_type_id', '=', shift_type_id), ('partner_id', '=', False)], order='id asc')
                                    exist = False
                                    for line in register_plan_lines:
                                        _logger.info(u'队列计划明细ID:%d', line.id)
                                        # _logger.info(u'队列计划明细班次ID:%d', line.shift_type_id.id)
                                        # if line.shift_type_id.id != shift_type_id:
                                        #     continue
                                        # _logger.info(u'队列计划明细病人ID:%s', line.partner_id.id)
                                        # if line.partner_id:
                                        #     continue
                                        _logger.info(u'队列计划明细对应当天时间:%s', '%s %s:00' % (register_date, line.time_point_name))
                                        if datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) < current_time:
                                            continue

                                        time_point_name = line.time_point_name  # 号源的时间点
                                        register_source = register_source_obj.search([('date', '=', register_date), ('department_id', '=', dept_id), ('employee_id', '=', employee_id), ('time_point_name', '=', time_point_name)])
                                        _logger.info(u'队列计划明细对应号源ID:%s', register_source.id)
                                        if not register_source:
                                            continue

                                        _logger.info(u'队列计划明细对应号源状态:%s', register_source.state)
                                        if register_source.state != '0':
                                            continue

                                        try:
                                            register_source_obj.appointment_register(register_source.id) # 号源占用
                                            register_source_res = register_source.id
                                            line.write({
                                                'source': 'manual',
                                                'partner_id': partner.id,
                                                'register_time': register_datetime_str,
                                                'register_id': register.id,
                                            })
                                            vals.update({
                                                'appointment_number': line.medical_sort,  # 预约顺序号,
                                                'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 预约时间
                                            })
                                            exist = True
                                            break
                                        except:
                                            _logger.error(u'有挂号医生，修改队列计划明细出错')
                                            _logger.error(traceback.format_exc())
                                            continue

                                    if not exist:
                                        _logger.info(u'上午，没有预约记录，有挂号医生')
                                        medical_sort = max([line.medical_sort for line in register_plan.line_ids]) + 1

                                        line = register_plan_line_obj.create({
                                            'register_plan_id': register_plan.id,
                                            'medical_sort': medical_sort,
                                            'shift_type_id': shift_type_id,
                                            'time_point_name': current_time_str,
                                            'reserve_time_point_name': current_time_str,
                                            'source': 'manual',
                                            'partner_id': partner.id,
                                            'register_time': register_datetime_str,
                                            'register_id': register.id,
                                        })
                                        vals.update({
                                            'appointment_number': line.medical_sort,  # 预约顺序号,
                                            'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT), # 预约时间
                                        })
                                # ####中午休息####
                                elif first_shift_end_time < current_time < last_shift_start_time:
                                    _logger.info(u'中午休息')
                                    shift_type_id = shifts[-1].id # 科室班次
                                    _logger.info(u'当前班次ID:%d', shift_type_id)
                                    register_plan_lines = register_plan_line_obj.search([('register_plan_id', '=', register_plan.id), ('shift_type_id', '=', shift_type_id), ('partner_id', '=', False)], order='id asc')
                                    exist = False
                                    for line in register_plan_lines:
                                        _logger.info(u'队列计划明细ID:%d', line.id)
                                        # _logger.info(u'队列计划明细班次ID:%d', line.shift_type_id.id)
                                        # if line.shift_type_id.id != shift_type_id:
                                        #     continue
                                        # _logger.info(u'队列计划明细病人ID:%s', line.partner_id.id)
                                        # if line.partner_id:
                                        #     continue

                                        time_point_name = line.time_point_name  # 号源的时间点
                                        register_source = register_source_obj.search([('date', '=', register_date), ('department_id', '=', dept_id), ('employee_id', '=', employee_id), ('time_point_name', '=', time_point_name)])
                                        _logger.info(u'队列计划明细对应号源ID:%s', register_source.id)
                                        if not register_source:
                                            continue

                                        _logger.info(u'队列计划明细对应号源状态:%s', register_source.state)
                                        if register_source.state != '0':
                                            continue

                                        try:
                                            register_source_obj.appointment_register(register_source.id) # 号源占用
                                            register_source_res = register_source.id
                                            line.write({
                                                'source': 'manual',
                                                'partner_id': partner.id,
                                                'register_time': register_datetime_str,
                                                'register_id': register.id,
                                            })
                                            vals.update({
                                                'appointment_number': line.medical_sort,  # 预约顺序号,
                                                'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 预约时间
                                            })
                                            exist = True
                                            break
                                        except:
                                            _logger.error(u'有挂号医生，修改队列计划明细出错')
                                            _logger.error(traceback.format_exc())
                                            continue

                                    if not exist:
                                        _logger.info(u'中午休息，没有预约记录，有挂号医生')
                                        medical_sort = max([line.medical_sort for line in register_plan.line_ids]) + 1

                                        line = register_plan_line_obj.create({
                                            'register_plan_id': register_plan.id,
                                            'medical_sort': medical_sort,
                                            'shift_type_id': shift_type_id,
                                            'time_point_name': current_time_str,
                                            'reserve_time_point_name': current_time_str,
                                            'source': 'manual',
                                            'partner_id': partner.id,
                                            'register_time': register_datetime_str,
                                            'register_id': register.id,
                                        })
                                        vals.update({
                                            'appointment_number': line.medical_sort,  # 预约顺序号,
                                            'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT), # 预约时间
                                        })
                                # ####下午####
                                elif last_shift_start_time <= current_time <= last_shift_end_time:
                                    _logger.info(u'下午')
                                    shift_type_id = shifts[-1].id # 科室班次
                                    _logger.info(u'当前班次ID:%d', shift_type_id)
                                    register_plan_lines = register_plan_line_obj.search([('register_plan_id', '=', register_plan.id), ('shift_type_id', '=', shift_type_id), ('partner_id', '=', False)], order='id asc')
                                    exist = False
                                    for line in register_plan_lines:
                                        _logger.info(u'队列计划明细ID:%d', line.id)
                                        # _logger.info(u'队列计划明细班次ID:%d', line.shift_type_id.id)
                                        # if line.shift_type_id.id != shift_type_id:
                                        #     continue
                                        # _logger.info(u'队列计划明细病人ID:%s', line.partner_id.id)
                                        # if line.partner_id:
                                        #     continue
                                        _logger.info(u'队列计划明细对应当天时间:%s', '%s %s:00' % (register_date, line.time_point_name))
                                        if datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) < current_time:
                                            continue

                                        time_point_name = line.time_point_name  # 号源的时间点
                                        register_source = register_source_obj.search([('date', '=', register_date), ('department_id', '=', dept_id), ('employee_id', '=', employee_id), ('time_point_name', '=', time_point_name)])
                                        _logger.info(u'队列计划明细对应号源ID:%s', register_source.id)
                                        if not register_source:
                                            continue
                                        _logger.info(u'队列计划明细对应号源状态:%s', register_source.state)
                                        if register_source.state != '0':
                                            continue

                                        try:
                                            register_source_obj.appointment_register(register_source.id) # 号源占用
                                            register_source_res = register_source.id
                                            line.write({
                                                'source': 'manual',
                                                'partner_id': partner.id,
                                                'register_time': register_datetime_str,
                                                'register_id': register.id,
                                            })
                                            vals.update({
                                                'appointment_number': line.medical_sort,  # 预约顺序号,
                                                'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 预约时间
                                            })
                                            exist = True
                                            break
                                        except:
                                            _logger.error(u'有挂号医生，修改队列计划明细出错')
                                            _logger.error(traceback.format_exc())
                                            continue

                                    if not exist:
                                        _logger.info(u'下午，没有预约记录，有挂号医生')
                                        medical_sort = max([line.medical_sort for line in register_plan.line_ids]) + 1
                                        line = register_plan_line_obj.create({
                                            'register_plan_id': register_plan.id,
                                            'medical_sort': medical_sort,
                                            'shift_type_id': shift_type_id,
                                            'time_point_name': current_time_str,
                                            'reserve_time_point_name': current_time_str,
                                            'source': 'manual',
                                            'partner_id': partner.id,
                                            'register_time': register_datetime_str,
                                            'register_id': register.id,
                                        })
                                        vals.update({
                                            'appointment_number': line.medical_sort,  # 预约顺序号,
                                            'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT), # 预约时间
                                        })
                                # ####下班后####
                                else:
                                    _logger.info(u'下班后')
                                    shift_type_id = shifts[-1].id  # 科室班次
                                    medical_sort = max([line.medical_sort for line in register_plan.line_ids]) + 1
                                    line = register_plan_line_obj.create({
                                        'register_plan_id': register_plan.id,
                                        'medical_sort': medical_sort,
                                        'shift_type_id': shift_type_id,
                                        'time_point_name': current_time_str,
                                        'reserve_time_point_name': current_time_str,
                                        'source': 'manual',
                                        'partner_id': partner.id,
                                        'register_time': register_datetime_str,
                                        'register_id': register.id,
                                    })
                                    vals.update({
                                        'appointment_number': line.medical_sort,  # 预约顺序号,
                                        'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT), # 预约时间
                                    })
                        except:
                            _logger.error(u'有挂号医生，计算预约时间出错')
                            _logger.error(traceback.format_exc())
                    else:
                        _logger.info(u'无挂号医生')
                        # _logger.info(u'当前时间:%s', current_time)
                        # try:
                        #     # 科室对应的班次
                        #     shift_type = shift_type_obj.search([('department_id', '=', dept_id)])
                        #     if shift_type:
                        #         shifts = sorted(shift_type, key=lambda x: x.start_time)  # 班次
                        #         first_shift_start_time = today + timedelta(hours=shifts[0].start_time)  # 上午的上班时间
                        #         _logger.info(u'上午上班时间:%s', first_shift_start_time)
                        #         first_shift_end_time = today + timedelta(hours=shifts[0].end_time)  # 上午的下班时间
                        #         _logger.info(u'上午下班时间:%s', first_shift_end_time)
                        #         last_shift_start_time = today + timedelta(hours=shifts[-1].start_time)  # 下午的上班时间
                        #         _logger.info(u'下午上班时间:%s', last_shift_start_time)
                        #         last_shift_end_time = today + timedelta(hours=shifts[-1].end_time)  # 下午的下班时间
                        #         _logger.info(u'下午下班时间:%s', last_shift_end_time)
                        #
                        #         # ##########计算当前班次##########
                        #         # ####上班前####
                        #         if current_time < first_shift_start_time:
                        #             shift_type_id = shifts[0].id
                        #         # ####上午####
                        #         elif first_shift_start_time <= current_time <= first_shift_end_time:
                        #             shift_type_id = shifts[0].id
                        #         # ####中午休息####
                        #         elif first_shift_end_time < current_time < last_shift_start_time:
                        #             shift_type_id = shifts[-1].id
                        #         # ####下午####
                        #         elif last_shift_start_time <= current_time <= last_shift_end_time:
                        #             shift_type_id = shifts[-1].id
                        #         # ####下班后####
                        #         else:
                        #             shift_type_id = shifts[-1].id
                        #
                        #         shift_type_name = shift_type_obj.browse(shift_type_id).name
                        #         _logger.info(u'班次ID:%s, 班次名称:%s', shift_type_id, shift_type_name)
                        #
                        #
                        #         register_type = res['register_type'].decode('utf8') # 号类
                        #         _logger.info(u'号类名称:%s', register_type)
                        #         _logger.info(u'挂号科室Id:%s, 科室名称:%s, 就诊日期:%s', dept_id, department_obj.browse(dept_id).name, register_date)
                        #         max_queue_count = 2000
                        #         select_doctor_id = False
                        #         schedules = work_schedule_obj.search([('department_id', '=', dept_id), ('date', '=', register_date)])
                        #         _logger.info(u'挂号安排数量:%s', len(schedules))
                        #         for schedule in schedules: # 当前科室的挂号安排
                        #             registered_type = [registered_type.name for registered_type in schedule.employee_id.registered_type_ids]
                        #             _logger.info(u'当前医生%s所看号类数量:%s, 所看号类名称:%s', schedule.employee_id.name, len(registered_type), u'|'.join(registered_type))
                        #             if register_type not in registered_type: # 医生所看号类
                        #                 _logger.info(u'挂号号类:%s不在当前医生%s所看号类:%s中', register_type, schedule.employee_id.name, u'|'.join(registered_type))
                        #                 continue
                        #
                        #             shift_type_ids = [shift.shift_type_id.id for shift in schedule.shifts if not shift.is_stop]
                        #             _logger.info(u'当前医生当天挂号安排班次IDS:%s', u','.join(map(lambda x: str(x), shift_type_ids)))
                        #             if shift_type_id not in shift_type_ids: # 当前计划是否有当前班次对应的排班
                        #                 _logger.info(u'班次ID:%s不在当前医生%s的挂号安排班次IDS:%s中', shift_type_id, schedule.employee_id.name, shift_type_ids)
                        #                 continue
                        #
                        #             register_plan = register_plan_obj.search([('medical_date', '=', register_date), ('department_id', '=', dept_id), ('employee_id', '=', schedule.employee_id.id)])  # 队列计划
                        #             _logger.info(u'队列计划ID:%d', register_plan.id)
                        #
                        #             lines = register_plan_line_obj.search([('register_plan_id', '=', register_plan.id), ('partner_id', '!=', False)]) # 队列计划明细(已挂号的)
                        #             _logger.info(u'当前医生%s已挂号数量:%s', schedule.employee_id.name, len(lines))
                        #             if len(lines) < max_queue_count:
                        #                 max_queue_count = len(lines)
                        #                 select_doctor_id = schedule.employee_id.id
                        #
                        #         _logger.info(u'自动选择医生ID:%s', select_doctor_id)
                        #         if select_doctor_id:
                        #             register_plan = register_plan_obj.search([('medical_date', '=', register_date), ('department_id', '=', dept_id), ('employee_id', '=', select_doctor_id)])  # 队列计划
                        #             register_plan_lines = register_plan_line_obj.search([('register_plan_id', '=', register_plan.id), ('shift_type_id', '=', shift_type_id), ('partner_id', '=', False)], order='id asc')
                        #             _logger.info(u'队列计划ID:%d', register_plan.id)
                        #
                        #             # 计算当前时间对应科室的班次
                        #             #    上班前              上午                 休息              下午               下班后
                        #             # ____________|__________________________|__________|__________________________|____________
                        #
                        #             # ####上班前####
                        #             if current_time < first_shift_start_time:
                        #                 _logger.info(u'上班前')
                        #                 for line in register_plan_lines:
                        #                     _logger.info(u'队列计划明细ID:%d', line.id)
                        #                     # if line.shift_type_id.id != shift_type_id:
                        #                     #     continue
                        #                     #
                        #                     # if line.partner_id:
                        #                     #     continue
                        #
                        #                     time_point_name = line.time_point_name  # 号源的时间点
                        #                     register_source = register_source_obj.search([('date', '=', register_date), ('department_id', '=', dept_id), ('employee_id', '=', select_doctor_id), ('time_point_name', '=', time_point_name)])
                        #                     _logger.info(u'队列计划明细对应号源ID:%s', register_source.id)
                        #                     if not register_source:
                        #                         continue
                        #                     _logger.info(u'队列计划明细对应号源状态:%s', register_source.state)
                        #                     if register_source.state != '0':
                        #                         continue
                        #
                        #                     try:
                        #                         register_source_obj.appointment_register(register_source.id) # 号源占用
                        #                         register_source_res = register_source.id
                        #                         line.write({
                        #                             'source': 'manual',
                        #                             'partner_id': partner.id,
                        #                             'register_time': register_datetime_str,
                        #                             'register_id': register.id,
                        #                         })
                        #                         vals.update({
                        #                             'appointment_number': line.medical_sort,  # 预约顺序号,
                        #                             'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 预约时间
                        #                             'employee_id': select_doctor_id
                        #                         })
                        #                         break
                        #                     except:
                        #                         _logger.error(u'无挂号医生，修改队列计划明细出错')
                        #                         _logger.error(traceback.format_exc())
                        #                         continue
                        #             # ####上午####
                        #             elif first_shift_start_time <= current_time <= first_shift_end_time:
                        #                 _logger.info(u'上午')
                        #                 exist = False
                        #                 for line in register_plan_lines:
                        #                     _logger.info(u'队列计划明细ID:%d', line.id)
                        #                     # if line.shift_type_id.id != shift_type_id:
                        #                     #     continue
                        #                     # if line.partner_id:
                        #                     #     continue
                        #                     _logger.info(u'队列计划明细对应当天时间:%s', '%s %s:00' % (register_date, line.time_point_name))
                        #                     if datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) < current_time:
                        #                         continue
                        #
                        #                     time_point_name = line.time_point_name  # 号源的时间点
                        #                     register_source = register_source_obj.search([('date', '=', register_date), ('department_id', '=', dept_id), ('employee_id', '=', select_doctor_id), ('time_point_name', '=', time_point_name)])
                        #                     _logger.info(u'队列计划明细对应号源ID:%s', register_source.id)
                        #                     if not register_source:
                        #                         continue
                        #
                        #                     _logger.info(u'队列计划明细对应号源状态:%s', register_source.state)
                        #                     if register_source.state != '0':
                        #                         continue
                        #
                        #                     try:
                        #                         register_source_obj.appointment_register(register_source.id) # 号源占用
                        #                         register_source_res = register_source.id
                        #                         line.write({
                        #                             'source': 'manual',
                        #                             'partner_id': partner.id,
                        #                             'register_time': register_datetime_str,
                        #                             'register_id': register.id,
                        #                         })
                        #                         vals.update({
                        #                             'appointment_number': line.medical_sort,  # 预约顺序号,
                        #                             'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 预约时间
                        #                             'employee_id': select_doctor_id
                        #                         })
                        #                         exist = True
                        #                         break
                        #                     except:
                        #                         _logger.error(u'无挂号医生，修改队列计划明细出错')
                        #                         _logger.error(traceback.format_exc())
                        #                         continue
                        #
                        #                 if not exist:
                        #                     _logger.info(u'上午，没有预约记录，无挂号医生')
                        #                     medical_sort = max([line.medical_sort for line in register_plan.line_ids]) + 1
                        #                     line = register_plan_line_obj.create({
                        #                         'register_plan_id': register_plan.id,
                        #                         'medical_sort': medical_sort,
                        #                         'shift_type_id': shift_type_id,
                        #                         'time_point_name': current_time_str,
                        #                         'reserve_time_point_name': current_time_str,
                        #                         'source': 'manual',
                        #                         'partner_id': partner.id,
                        #                         'register_time': register_datetime_str,
                        #                         'register_id': register.id,
                        #                     })
                        #                     vals.update({
                        #                         'appointment_number': line.medical_sort,  # 预约顺序号,
                        #                         'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT), # 预约时间
                        #                         'employee_id': select_doctor_id
                        #                     })
                        #             # ####中午休息####
                        #             elif first_shift_end_time < current_time < last_shift_start_time:
                        #                 _logger.info(u'中午休息')
                        #                 for line in register_plan_lines:
                        #                     _logger.info(u'队列计划明细ID:%d', line.id)
                        #                     # if line.shift_type_id.id != shift_type_id:
                        #                     #     continue
                        #                     # if line.partner_id:
                        #                     #     continue
                        #
                        #                     time_point_name = line.time_point_name  # 号源的时间点
                        #                     register_source = register_source_obj.search([('date', '=', register_date), ('department_id', '=', dept_id), ('employee_id', '=', select_doctor_id), ('time_point_name', '=', time_point_name)])
                        #                     _logger.info(u'队列计划明细对应号源ID:%s', register_source.id)
                        #                     if not register_source:
                        #                         continue
                        #                     _logger.info(u'队列计划明细对应号源状态:%s', register_source.state)
                        #                     if register_source.state != '0':
                        #                         continue
                        #
                        #                     try:
                        #                         register_source_obj.appointment_register(register_source.id) # 号源占用
                        #                         register_source_res = register_source.id
                        #                         line.write({
                        #                             'source': 'manual',
                        #                             'partner_id': partner.id,
                        #                             'register_time': register_datetime_str,
                        #                             'register_id': register.id,
                        #                         })
                        #                         vals.update({
                        #                             'appointment_number': line.medical_sort,  # 预约顺序号,
                        #                             'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 预约时间
                        #                             'employee_id': select_doctor_id
                        #                         })
                        #                         break
                        #                     except:
                        #                         _logger.error(u'无挂号医生，修改队列计划明细出错')
                        #                         _logger.error(traceback.format_exc())
                        #                         continue
                        #             # ####下午####
                        #             elif last_shift_start_time <= current_time <= last_shift_end_time:
                        #                 _logger.info(u'下午')
                        #                 exist = False
                        #                 for line in register_plan_lines:
                        #                     _logger.info(u'队列计划明细ID:%d', line.id)
                        #                     # if line.shift_type_id.id != shift_type_id:
                        #                     #     continue
                        #                     # if line.partner_id:
                        #                     #     continue
                        #                     _logger.info(u'队列计划明细对应当天时间:%s', '%s %s:00' % (register_date, line.time_point_name))
                        #                     if datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) < current_time:
                        #                         continue
                        #
                        #                     time_point_name = line.time_point_name  # 号源的时间点
                        #                     register_source = register_source_obj.search([('date', '=', register_date), ('department_id', '=', dept_id), ('employee_id', '=', select_doctor_id), ('time_point_name', '=', time_point_name)])
                        #                     _logger.info(u'队列计划明细对应号源ID:%s', register_source.id)
                        #                     if not register_source:
                        #                         continue
                        #                     _logger.info(u'队列计划明细对应号源状态:%s', register_source.state)
                        #                     if register_source.state != '0':
                        #                         continue
                        #
                        #                     try:
                        #                         register_source_obj.appointment_register(register_source.id) # 号源占用
                        #                         register_source_res = register_source.id
                        #                         line.write({
                        #                             'source': 'manual',
                        #                             'partner_id': partner.id,
                        #                             'register_time': register_datetime_str,
                        #                             'register_id': register.id,
                        #                         })
                        #                         vals.update({
                        #                             'appointment_number': line.medical_sort,  # 预约顺序号,
                        #                             'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 预约时间
                        #                             'employee_id': select_doctor_id
                        #                         })
                        #                         exist = True
                        #                         break
                        #                     except:
                        #                         _logger.error(u'无挂号医生，修改队列计划明细出错')
                        #                         _logger.error(traceback.format_exc())
                        #                         continue
                        #
                        #                 if not exist:
                        #                     _logger.info(u'下午，没有预约记录，无挂号医生')
                        #                     medical_sort = max([line.medical_sort for line in register_plan.line_ids]) + 1
                        #                     line = register_plan_line_obj.create({
                        #                         'register_plan_id': register_plan.id,
                        #                         'medical_sort': medical_sort,
                        #                         'shift_type_id': shift_type_id,
                        #                         'time_point_name': current_time_str,
                        #                         'reserve_time_point_name': current_time_str,
                        #                         'source': 'manual',
                        #                         'partner_id': partner.id,
                        #                         'register_time': register_datetime_str,
                        #                         'register_id': register.id,
                        #                     })
                        #                     vals.update({
                        #                         'appointment_number': line.medical_sort,  # 预约顺序号,
                        #                         'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT), # 预约时间
                        #                         'employee_id': select_doctor_id
                        #                     })
                        #             # ####下班后####
                        #             else:
                        #                 _logger.info(u'下班后')
                        #                 # shift_type_id = shifts[-1].id  # 科室班次
                        #                 medical_sort = max([line.medical_sort for line in register_plan.line_ids]) + 1
                        #                 line = register_plan_line_obj.create({
                        #                     'register_plan_id': register_plan.id,
                        #                     'medical_sort': medical_sort,
                        #                     'shift_type_id': shift_type_id,
                        #                     'time_point_name': current_time_str,
                        #                     'reserve_time_point_name': current_time_str,
                        #                     'source': 'manual',
                        #                     'partner_id': partner.id,
                        #                     'register_time': register_datetime_str,
                        #                     'register_id': register.id,
                        #                 })
                        #                 vals.update({
                        #                     'appointment_number': line.medical_sort,  # 预约顺序号,
                        #                     'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT), # 预约时间
                        #                     'employee_id': select_doctor_id
                        #                 })
                        #
                        #         else:
                        #             pass
                        #             # register_plan = register_plan_obj.search([('medical_date', '=', register_date), ('department_id', '=', dept_id)])  # 队列计划
                        #             # # 计算当前时间对应科室的班次
                        #             # #    上班前              上午                 休息              下午               下班后
                        #             # # ____________|__________________________|__________|__________________________|____________
                        #             #
                        #             # # ####上班前####
                        #             # if current_time < first_shift_start_time:
                        #             #     for line in register_plan.line_ids:
                        #             #         if line.shift_type_id.id != shift_type_id:
                        #             #             continue
                        #             #         if line.partner_id:
                        #             #             continue
                        #             #
                        #             #         time_point_name = line.time_point_name  # 号源的时间点
                        #             #         register_source = register_source_obj.search([('date', '=', register_date), ('department_id', '=', dept_id), ('employee_id', '=', employee_id), ('time_point_name', '=', time_point_name)])
                        #             #         if not register_source:
                        #             #             continue
                        #             #
                        #             #         if register_source.state != '0':
                        #             #             continue
                        #             #
                        #             #         try:
                        #             #             register_source_obj.appointment_register(register_source.id) # 号源占用
                        #             #             register_source_res = register_source.id
                        #             #             line.write({
                        #             #                 'source': 'manual',
                        #             #                 'partner_id': partner.id,
                        #             #                 'register_time': register_datetime_str,
                        #             #                 'register_id': register.id,
                        #             #             })
                        #             #             vals.update({
                        #             #                 'appointment_number': line.medical_sort,  # 预约顺序号,
                        #             #                 'appointment_time': (datetime.strptime('%s %s:00' % (register_date, line.time_point_name), DATETIME_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 预约时间
                        #             #                 'employee_id': select_doctor_id
                        #             #             })
                        #             #             break
                        #             #         except:
                        #             #             _logger.error(u'无挂号医生，修改队列计划明细出错')
                        #             #             _logger.error(traceback.format_exc())
                        #             #             continue
                        # except:
                        #     _logger.error(u'无挂号医生，计算预约时间出错')
                        #     _logger.error(traceback.format_exc())


            total_queue = total_queue_obj.create(vals)

            # 挂号记录与总队列关联
            register.total_queue_id = total_queue.id

            return total_queue, register_source_res


        partner_obj = self.env['res.partner']
        register_obj = self.env['his.register']  # 病人挂号记录
        employee_obj = self.env['hr.employee']  # 医生
        department_obj = self.env['hr.department']  # 科室
        total_queue_obj = self.env['hrp.total_queue']  # 总队列

        register_source_obj = self.env['his.register_source']  # 挂号号源
        shift_type_obj = self.env['his.shift_type']  # 班次类型
        reserve_record_obj = self.env['his.reserve_record'] # 预约记录
        register_plan_obj = self.env['his.register_plan'] # 挂号计划
        register_plan_line_obj = self.env['his.register_plan_line'] # 挂号计划表明细
        treatment_process_obj = self.env['hrp.treatment_process'] # 就医流程主记录
        treatment_process_line_obj = self.env['hrp.treatment_process_line'] # 就医流程明细记录
        # work_schedule_obj = self.env['his.work_schedule'] # 排班结果

        current_time = datetime.now() + timedelta(hours=8)  # 当前时间
        current_time_str = current_time.strftime('%H:%M')
        # today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT) + timedelta(hours=8)
        today = datetime.strptime((datetime.now() + timedelta(hours=8)).strftime(DATE_FORMAT), DATE_FORMAT)
        _logger.info(u'今天日期:%s', today)
        now = datetime.now() + timedelta(hours=8) + timedelta(minutes=5)
        key_field_last_value = datetime.strptime('2010-01-01 00:00:00', DATETIME_FORMAT)
        for res in result:
            # 登记时间
            register_datetime = datetime.strptime(res['register_datetime'], DATETIME_FORMAT) # 登记时间
            register_datetime_str = (register_datetime - timedelta(hours=8)).strftime(DATETIME_FORMAT)
            if now > register_datetime > key_field_last_value:
                key_field_last_value = register_datetime

            # 挂号日期
            register_date = res['register_datetime'].split()[0]
            # 挂号科室
            department = department_obj.search([('his_id', '=', res['department_his_id'])])
            department_id = department.id

            # 挂号医生
            employee_id = False
            if res['employee_his_id']:
                employee_id = employee_obj.search([('his_id', '=', res['employee_his_id'])]).id
            # 操作员编号
            operator_code = res['operator_code']
            # 创建病人
            partner = create_partner()
            # 预约记录
            reserve_record = query_reserve_record()
            # 创建挂号记录
            register = create_register()
            # 修改预约记录
            if reserve_record:
                reserve_record.register_id = register.id
            # 创建挂号就医流程
            treatment_process_line = create_register_treatment_process()
            # 插入总队列
            register_source_res_id = None
            try:
                queue = None
                queue_res = create_queue()
                if queue_res:
                    queue = queue_res[0]
                    register_source_res_id = queue_res[1]


            except:
                if register_source_res_id:
                    if not module:
                        module.update({
                            'emqtt': importlib.import_module('odoo.addons.his_app_hcfy.models.emqtt'),
                            'config': importlib.import_module('odoo.tools.config')
                        })

                    payload = {
                        'action': 'write',
                        'data': {
                            'model': 'his.register_source',
                            'vals': {
                                "state": "0",
                                "internal_id": register_source_res_id
                            },
                        }
                    }
                    module['emqtt'].Emqtt.publish(module['config'].config['extranet_topic'], payload, 2)

                raise
            if treatment_process_line and queue and queue.appointment_time:
                appointment_time = (datetime.strptime(queue.appointment_time, DATETIME_FORMAT) + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M').split()
                treatment_process_line.message = '|'.join(appointment_time + ['A%03d' % int(queue.appointment_number), queue.employee_id.name or '']) # 就诊日期|时间点|预约号|医生名称



        if datetime.strptime(sync.key_field_last_value, DATETIME_FORMAT) < key_field_last_value:
            sync.key_field_last_value = key_field_last_value.strftime(DATETIME_FORMAT)

