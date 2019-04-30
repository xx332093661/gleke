# -*- encoding:utf-8 -*-
import logging
from datetime import datetime, timedelta

from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class SyncRegister(models.Model):
    _inherit = 'his.sync_define'


    def register_poll(self, result, sync):
        """挂号轮询回调"""
        def create_partner():
            """创建病人"""
            return partner_obj.create_partner({
                'his_id': res['partner_his_id'],  # HISID
                'outpatient_num': res['outpatient_num'],  # 门诊号
                'name': res['name'],  # 姓名
                'sex': res['sex'],  # 性别
                'id_no': res['id_no'],  # 身份证号
                'card_no': res['card_no'],  # 就诊卡号
                'medical_no': res['medical_no']  # 医保卡号
            })

        def create_register():
            """创建挂号记录"""
            register_res = register_obj.his_id_exist(res['his_id'])
            if register_res:
                return register_res

            employee_id = False
            if res['employee_his_id']:
                employee_id = employee_obj.search([('his_id', '=', res['employee_his_id'])]).id

            department_id = department_obj.search([('his_id', '=', res['department_his_id'])]).id

            register_res = register_obj.create({
                'his_id': res['his_id'],  # HISID
                'receipt_no': res['receipt_no'],  # NO(单据号)
                'record_state': res['record_state'],  # 记录状态
                'exe_state': res['exe_state'],  # 执行状态
                'register_type': res['register_type'],  # 号类名称
                'employee_id': employee_id,  # 医生
                'department_id': department_id,  # 科室
                'is_emerg_treat': res['is_emerg_treat'],  # 是否急诊
                # 'fee_name': res['fee_name'],  # 收费项目名称
                'register_datetime': res['register_datetime'],  # 登记时间
                'register_date': res['register_datetime'].split()[0],  # 登记日期
                'partner_id': partner.id,  # 病人
            })

            return register_res

        def create_queue():
            """创建队列"""
            if res['record_state'] in [2, 3]: # his中退号会新建病人挂号记录, 这里不作处理
                return

            if res['exe_state'] != 0: # 已执行, 不做处理
                return

            if register.total_queue_id: # 重复处理
                return

            total_queue = total_queue_obj.create({
                'outpatient_num': partner.outpatient_num,  # 门诊号
                'partner_id': partner.id,
                'business': '就诊',  # 业务类型
                'department_id': register.department_id.id,
                # 'room_id': False,  # 挂号诊室
                'employee_id': register.employee_id.id,
                'register_type': res['register_type'], # 号类
                'part': False,  # 部位
                'coll_method': False,  # 采集方式
                'is_emerg_treat': res['is_emerg_treat'],  # 是否急诊
                'origin': '1',  # 病人来源 1-门诊 2-住院
                'enqueue_datetime': fields.Datetime.now(),  # 入队时间
                'state': None,

                'origin_table': 'register',  # 来源表
                'origin_id': register.id,  # 对应来源表的ID
            })

            # 挂号记录与总队列关联
            register.total_queue_id = total_queue.id


        partner_obj = self.env['res.partner']
        register_obj = self.env['his.register']  # 病人挂号记录
        employee_obj = self.env['hr.employee']  # 医生
        department_obj = self.env['hr.department']  # 科室
        total_queue_obj = self.env['hrp.total_queue']  # 总队列

        now = datetime.now() + timedelta(hours=8) + timedelta(minutes=5)
        key_field_last_value = datetime.strptime('2010-01-01 00:00:00', DEFAULT_SERVER_DATETIME_FORMAT)
        for res in result:
            register_datetime = datetime.strptime(res['register_datetime'], DEFAULT_SERVER_DATETIME_FORMAT)
            if now > register_datetime > key_field_last_value:
                key_field_last_value = register_datetime

            # 创建病人
            partner = create_partner()
            # 创建挂号记录
            register = create_register()
            # 插入总队列
            create_queue()

        if datetime.strptime(sync.key_field_last_value, DEFAULT_SERVER_DATETIME_FORMAT) < key_field_last_value:
            sync.key_field_last_value = key_field_last_value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)










