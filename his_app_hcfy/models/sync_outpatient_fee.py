# -*- encoding:utf-8 -*-
import logging
from datetime import datetime, timedelta

from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)



class SyncOutpatientFee(models.Model):
    _inherit = 'his.sync_define'


    def outpatient_fee_poll(self, result, sync):
        def create_outpatient_fee():
            outpatient_fee_res = outpatient_fee_obj.search([('his_id', '=', res['his_id'])])
            if outpatient_fee_res:
                vals = {}
                if outpatient_fee_res.record_state != record_state:
                    vals['record_state'] = record_state
                    # outpatient_fee_res.record_state = record_state

                # 关联医嘱记录
                if not outpatient_fee_res.dispose_id:
                    if res['dispose_id']:
                        dispose = dispose_obj.search([('his_id', '=', res['dispose_id'])])
                        if dispose:
                            vals['dispose_id'] = dispose.id

                if vals:
                    outpatient_fee_res.write(vals)

                return outpatient_fee_res

            return outpatient_fee_obj.create(res)

        def get_disposes():
            """返回门诊费用对应的所有医嘱"""
            disposes = []
            # 对应医嘱
            dispose = outpatient_fee.dispose_id
            if not dispose:
                return disposes

            disposes.append(dispose)

            # 医嘱对应的相关医嘱
            if dispose.relation_dispose_id:
                relation_dispose = dispose_obj.search([('his_id', '=', dispose.relation_dispose_id)])
                if relation_dispose:
                    exist = False
                    for dispose in disposes:
                        if dispose.id == relation_dispose.id:
                            exist = True
                            break

                    if not exist:
                        disposes.append(relation_dispose)

            for relation_dispose in dispose_obj.search([('relation_dispose_id', '=', outpatient_fee.dispose_id.his_id)]):
                exist = False
                for dispose in disposes:
                    if dispose.id == relation_dispose.id:
                        exist = True
                        break

                if not exist:
                    disposes.append(relation_dispose)

            return disposes

        def create_queue():
            """入队列"""
            def create_examination_queue():
                """创建检查检验队列"""
                # 医嘱记录对应的诊疗项目目录没有对应的业务类型
                business = dispose.item_id.business_id
                if not business:
                    return

                total_queue = total_queue_obj.create({
                    'outpatient_num': dispose.partner_id.outpatient_num,  # 门诊号
                    'partner_id': dispose.partner_id.id,
                    'business': business.name,  # 业务类型
                    'department_id': dispose.department_id.id,
                    'room_id': False,  # 挂号诊室
                    'employee_id': False,  # 医生
                    'register_type': False,  # 号类
                    'part': dispose.part,  # 部位
                    'coll_method': dispose.method,  # 采集方式
                    'is_emerg_treat': False,  # 是否急诊
                    'origin': str(dispose.origin),  # 病人来源 1-门诊 2-住院
                    'enqueue_datetime': fields.Datetime.now(),  # 入队时间
                    'state': None,

                    'origin_table': 'dispose',  # 来源表
                    'origin_id': dispose.id,  # 对应来源表的ID
                })

                # 挂号记录与总队列关联
                dispose.total_queue_id = total_queue.id

            def create_drug_queue():
                """创建发药队列"""
                room_id = False
                if res['win_num']:
                    department = department_obj.search([('name', '=', res['win_num'])])  # 发药窗口
                    if department:
                        room_id = department.id

                partner = dispose.partner_id
                # department = dispose.department_id
                # 发药队列存在
                his_queue = total_queue_obj.search([('partner_id', '=', partner.id), ('business', '=', u'发药'), ('state', '=', None), ('date_state', '=', '1')], order='id desc', limit=1)
                if his_queue:
                    create_date = datetime.strptime(his_queue.create_date, DEFAULT_SERVER_DATETIME_FORMAT)
                    _logger.info(u'发药队列存在，创奸时间:%s', create_date)
                    if current_date < create_date + timedelta(minutes=5):
                        return

                total_queue = total_queue_obj.create({
                    'outpatient_num': partner.outpatient_num,  # 门诊号
                    'partner_id': partner.id,
                    'business': '发药',  # 业务类型
                    'department_id': dispose.department_id.id,
                    'room_id': room_id,  # 窗口号
                    'employee_id': False,  # 医生
                    'register_type': False,  # 号类
                    'part': False,  # 部位
                    'coll_method': False,  # 采集方式
                    'is_emerg_treat': False,  # 是否急诊
                    'origin': str(dispose.origin),  # 病人来源 1-门诊 2-住院
                    'enqueue_datetime': fields.Datetime.now(),  # 入队时间
                    'state': None,

                    'origin_table': 'dispose',  # 来源表
                    'origin_id': dispose.id,  # 对应来源表的ID
                })
                # 医嘱发送与总队列关联
                dispose.total_queue_id = total_queue.id

            for dispose in get_disposes():
                # 中处理门诊病人
                if dispose.origin != 1:
                    continue

                if not dispose.clinic_type:
                    continue

                # 队列已存在
                if dispose.total_queue_id:
                    continue

                # 发药
                if dispose.clinic_type in u'567':  # 诊疗类别是发药
                    create_drug_queue()
                    continue

                # 检查检验
                create_examination_queue()

        def update_dispose_queue_to_return():
            """退费"""
            # 对应的医嘱
            for dispose in get_disposes():
                # 总队列
                total_queue = dispose.total_queue_id

                if not total_queue:
                    continue
                # 退费
                if total_queue.state != '1':
                    total_queue.state = '1'

        def create_register_treatment_process():
            """缴费就医流程"""
            if not res['receipt_no']: # 没有挂号单
                return

            # 当前正在进行的就医流程
            process_id = False
            for line in treatment_process_line_obj.search([('code', '=', '01'), ('receipt_no', '=', res['receipt_no'])]): # 挂号就医流程
                if line.process_id.partner_id.id == outpatient_fee.partner_id.id:
                    process_id = line.process_id.id
                    break

            if not process_id:
                return

            if record_state == 0:  # 待缴费
                # _logger.info(u'缴费创建就医流程,process_id:%s, receipt_no:%s', process_id, res['receipt_no'])
                line_res = treatment_process_line_obj.search([('process_id', '=', process_id), ('code', '=', '03'), ('receipt_no', '=', res['receipt_no']), ('state', '=', 'doing')])
                # _logger.info(u'缴费创建就医流程,查询已创建的流程结果:%s', len(line_res))
                if line_res:
                    return

                # 与上一次缴费的时间间隔小于4分钟，不创建流程
                line_res = treatment_process_line_obj.search([('process_id', '=', process_id), ('code', '=', '03'), ('receipt_no', '=', res['receipt_no'])], order='id desc', limit=1)
                if line_res:
                    create_date = datetime.strptime(line_res.create_date, DEFAULT_SERVER_DATETIME_FORMAT)
                    if create_date + timedelta(minutes=4) >= datetime.now():
                        return




                treatment_process_line_obj.create({
                    'process_id': process_id,
                    'name': '缴费',
                    'code': '03',
                    'business': '缴费',  # 业务类型
                    'department_id': False,
                    'employee_id': False,
                    'location': u'1楼缴费窗口，1楼自助机',
                    'process_type': '2', # 流程类型 '1', '排队'  '2', '不排队'
                    'state': 'doing',
                    'receipt_no': res['receipt_no'], # 挂号单号
                })
            else:
                treatment_process_line = treatment_process_line_obj.search([('process_id', '=', process_id), ('code', '=', '03'), ('receipt_no', '=', res['receipt_no']), ('state', '=', 'doing')])
                if treatment_process_line:
                    treatment_process_line.write({'state': 'done'})

                treatment_process_line = treatment_process_line_obj.search([('process_id', '=', process_id), ('code', '=', '06'), ('state', '=', 'doing')])
                if treatment_process_line:
                    treatment_process_line.write({'state': 'done'})




        total_queue_obj = self.env['hrp.total_queue']  # 总队列
        department_obj = self.env['hr.department']  # 科室
        dispose_obj = self.env['his.dispose'] # 医嘱
        outpatient_fee_obj = self.env['his.outpatient_fee'] # 门诊费用记录
        # treatment_process_obj = self.env['hrp.treatment_process'] # 就医流程主记录
        treatment_process_line_obj = self.env['hrp.treatment_process_line'] # 就医流程明细记录

        # today = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        now = datetime.now() + timedelta(hours=8) + timedelta(minutes=5)
        key_field_last_value = datetime.strptime('2010-01-01 00:00:00', DEFAULT_SERVER_DATETIME_FORMAT)
        current_date = datetime.now()
        _logger.info(u'同步门诊费用，当前时间:%s', current_date)
        for res in result:
            register_datetime = datetime.strptime(res['register_datetime'], DEFAULT_SERVER_DATETIME_FORMAT)
            if now > register_datetime > key_field_last_value:
                key_field_last_value = register_datetime

            record_state = res['record_state']  # 记录状态
            # 创建门诊费用记录
            outpatient_fee = create_outpatient_fee()

            # 不处理挂号
            if res['record_prototype'] == 4: # 记录性质
                continue


            # 创建或修改缴费就医流程
            create_register_treatment_process()

            # 已缴费
            if record_state == 1:
                create_queue()
                continue

            # 退费
            if record_state == 2:
                update_dispose_queue_to_return()


        if datetime.strptime(sync.key_field_last_value, DEFAULT_SERVER_DATETIME_FORMAT) < key_field_last_value:
            sync.key_field_last_value = key_field_last_value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)


