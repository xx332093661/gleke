# -*- encoding:utf-8 -*-
import logging
import os

from datetime import datetime, timedelta

from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'



class SyncDisposeSend(models.Model):
    _inherit = 'his.sync_define'


    def dispose_send_poll(self, result, sync):
        """病人医嘱发送轮询回调"""
        def create_partner():
            """创建病人"""
            return partner_obj .create_partner({
                'his_id': res['partner_his_id'],  # HISID
                'outpatient_num': res['outpatient_num'],  # 门诊号
                'hospitalize_no': res['hospitalize_no'],  # 住院号
                'name': res['name'],  # 姓名
                'sex': res['sex'],  # 性别
                'gender': 'male' if res['sex'] == u'男' or res['sex'] == '男' else 'female',  # 性别
                'id_no': res['id_no'],  # 身份证号
                'card_no': res['card_no'],  # 就诊卡号
                'medical_no': res['medical_no'],  # 医保卡号
                'is_patient': True,  # 是患者,
                'birth_date': res['birth_date'].split()[0]
            })

        def create_dispose():
            """创建医嘱记录"""
            dispose_res = dispose_obj.his_id_exist(res['dispose_id'])
            if dispose_res:
                return dispose_res

            return dispose_obj.create({
                'his_id': res['dispose_id'],  # 医嘱ID
                'relation_dispose_id': res['relation_dispose_id'],  # 相关ID
                'clinic_type': res['clinic_type'],  # 诊疗类别
                'item_id': clinic_item_category_obj.his_id_exist(res['item_id']).id,  # 诊疗项目ID
                'part': res['part'],  # 标本部位
                'method': res['method'],  # 检查方法
                'department_id': department_obj.his_id_exist(res['department_id']).id,  # 执行科室ID
                'origin': res['origin'],  # 病人来源
                'dispose_datetime': res['dispose_datetime'],  # 开嘱时间
                'dispose_date': res['dispose_datetime'].split()[0],  # 开嘱日期
                'partner_id': partner.id,  # 病人
                'receipt_no': res['receipt_no'], # 挂号单

                'amount_total': res['amount_total'], # 总给予量
                'days': res['days'], # 天数
                'frequency': res['frequency'], # 频率次数
                'frequency_interval': res['frequency_interval'], # 频率间隔
                'interval_unit': res['interval_unit'], # 间隔单位

            })

        def create_dispose_send():
            """创建医嘱发送"""
            if dispose_send_obj.search([('send_no', '=', res['send_no']), ('dispose_serial_number', '=', res['dispose_id'])]):
                return

            dispose_send_obj.create({
                'send_no': res['send_no'],  # 发送号
                'dispose_serial_number': res['dispose_id'],  # 医嘱ID
                'send_datetime': res['send_datetime'],  # 发送时间
                'send_date': res['send_datetime'].split()[0],  # 发送日期
                'exe_room': res['exe_room'],  # 执行间
                'exe_process': res['exe_process'],  # 执行过程
                'register_datetime': res['register_datetime'],  # 报到时间
                'dispose_id': dispose.id  # 医嘱
            })

        def register_done():
            """就诊队列完诊"""
            register = register_obj.search([('receipt_no', '=', res['receipt_no']), ('partner_id', '=', partner.id), ('record_state', '=', 1)])
            if not register:
                return

            total_queue = register.total_queue_id
            if not total_queue:
                return

            if total_queue.state != '2':
                total_queue.state = '2'  # 完诊

        def create_queue():
            """创建队列"""
            if res['origin'] != 2: # 只处理门诊病人
                return

            # # 医嘱的诊疗项目编码为360000115 3600001168 3600001557 3600001558 360000121的直接进队列 因为是免费的
            # if dispose.item_id.code not in ['360000115', '3600001168', '3600001557', '3600001558', '360000121']:
            #     return

            # 业务类型
            business = dispose.item_id.business_id
            if not business:
                return

            # 总队列已存在
            if dispose.total_queue_id:
                return

            total_queue = total_queue_obj.create({
                'outpatient_num': partner.outpatient_num,  # 门诊号(住院号)
                'partner_id': partner.id,
                'business': business.name,  # 业务类型
                'department_id': dispose.department_id.id,
                'room_id': False,  # 挂号诊室
                'employee_id': False,  # 医生
                'register_type': False,  # 号类
                'part': res['part'],  # 部位
                'coll_method': res['method'],  # 采集方式
                'is_emerg_treat': False,  # 是否急诊
                'origin': str(res['origin']),  # 病人来源 1-门诊 2-住院
                'enqueue_datetime': fields.Datetime.now(),  # 入队时间
                'state': None,

                'origin_table': 'dispose',  # 来源表
                'origin_id': dispose.id,  # 对应来源表的ID

                'count': dispose.amount_total,
            })

            # 医嘱发送与总队列关联
            dispose.total_queue_id = total_queue.id


        partner_obj = self.env['res.partner']
        dispose_obj = self.env['his.dispose']  # 病人医嘱记录
        clinic_item_category_obj = self.env['his.clinic_item_category'] # 诊疗项目目录
        department_obj = self.env['hr.department'] # 科室
        dispose_send_obj = self.env['his.dispose_send'] # 医嘱发送记录
        total_queue_obj = self.env['hrp.total_queue']
        register_obj = self.env['his.register'] # 病人挂号记录

        now = datetime.now() + timedelta(hours=8) + timedelta(minutes=5)

        key_field_last_value = datetime.strptime('2010-01-01 00:00:00', DEFAULT_SERVER_DATETIME_FORMAT)

        for res in result:
            send_datetime = datetime.strptime(res['send_datetime'], DEFAULT_SERVER_DATETIME_FORMAT)
            if now > send_datetime > key_field_last_value:
                key_field_last_value = send_datetime

            # 创建病人
            partner = create_partner()
            # 创建医嘱记录
            dispose = create_dispose()
            # 创建医嘱发送
            create_dispose_send()
            # 就诊队列完诊
            register_done()
            # 住院病人检验检查进入队列
            create_queue()

        if datetime.strptime(sync.key_field_last_value, DEFAULT_SERVER_DATETIME_FORMAT) < key_field_last_value:
            sync.key_field_last_value = key_field_last_value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)





