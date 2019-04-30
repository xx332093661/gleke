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

            for dispose in get_disposes():
                # 中处理门诊病人
                if dispose.origin != 1:
                    continue

                if not dispose.clinic_type:
                    continue

                # 队列已存在
                if dispose.total_queue_id:
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

        def update_register_queue_to_return():
            """挂号退费"""
            partner = partner_obj.search([('his_id', '=', res['partner_his_id'])])
            # 计算挂号记录
            register = register_obj.search([('receipt_no', '=', res['receipt_no']), ('partner_id', '=', partner.id), ('record_state', '=', 1)])
            if not register:
                return
            total_queue = register.total_queue_id
            if total_queue:
                if total_queue.state != '1':
                    total_queue.state = '1'  # 退号

            if register.record_state != 3: # 退费
                register.record_state = 3


        total_queue_obj = self.env['hrp.total_queue']  # 总队列
        dispose_obj = self.env['his.dispose'] # 医嘱
        outpatient_fee_obj = self.env['his.outpatient_fee'] # 门诊费用记录
        register_obj = self.env['his.register'] # 病人挂号记录
        partner_obj = self.env['res.partner']


        now = datetime.now() + timedelta(hours=8) + timedelta(minutes=5)
        key_field_last_value = datetime.strptime('2010-01-01 00:00:00', DEFAULT_SERVER_DATETIME_FORMAT)

        for res in result:
            register_datetime = datetime.strptime(res['register_datetime'], DEFAULT_SERVER_DATETIME_FORMAT)
            if now > register_datetime > key_field_last_value:
                key_field_last_value = register_datetime

            # 创建门诊费用记录
            outpatient_fee = create_outpatient_fee()

            # 不处理挂号
            if res['record_prototype'] == 4: # 记录性质
                continue

            record_state = res['record_state']  # 记录状态
            # 已缴费
            if record_state == 1:
                create_queue()
                continue

            # 退费
            if record_state == 2:
                update_dispose_queue_to_return()

        if datetime.strptime(sync.key_field_last_value, DEFAULT_SERVER_DATETIME_FORMAT) < key_field_last_value:
            sync.key_field_last_value = key_field_last_value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)


