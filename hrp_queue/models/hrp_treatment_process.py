# coding:utf-8

from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from ..models.hrp_mqtt import module
from hrp_const import time_to_client
from hrp_queue import STATE

import traceback
import logging

_logger = logging.getLogger(__name__)


class HrpTreatmentProcess(models.Model):
    _name = 'hrp.treatment_process'
    _description = u'就医流程'

    partner_id = fields.Many2one('res.partner', '患者')
    visit_date = fields.Date('就诊日期')

    line_ids = fields.One2many('hrp.treatment_process_line', 'process_id', '流程明细')

    state = fields.Selection([('doing', '进行中'), ('done', '完成')], '状态', default='doing')

    _rec_name = 'partner_id'
    _order = 'visit_date desc'

    def get_process(self, data):
        """获取就医流程"""
        m_partner = self.env['res.partner']
        treatment_process_line_obj = self.env['hrp.treatment_process_line']

        prev_partner_id = data.get('prev_partner_id')
        current_partner_id = data['current_partner_id']
        topic = data['topic']

        # 清除之前患者topic
        prev_partner = m_partner.search([('id', '=', prev_partner_id)])
        if prev_partner:
            prev_partner.topic = False

        partner = m_partner.search([('id', '=', current_partner_id)])
        res = {}
        if not partner:
            return res
        # 记录当前用户topic
        partner.topic = topic

        today = (datetime.now() + timedelta(hours=8)).strftime(DEFAULT_SERVER_DATE_FORMAT)

        # 当天
        process = self.search([('partner_id', '=', current_partner_id), ('state', '=', 'doing'), ('visit_date', '=', today)], order='id desc', limit=1)
        if not process:
            # 以后
            process = self.search([('partner_id', '=', current_partner_id), ('state', '=', 'doing')], order='id desc', limit=1)
            if not process:
                return res

        res.update({
            'partner_id': process.partner_id.id,
            'visit_date': process.visit_date,
            'treatment_details': []
        })

        # 查询子流程
        treatment_process_lines = treatment_process_line_obj.search([('process_id', '=', process.id)], order='update_time, id')

        for line in treatment_process_lines:
            line_data = line.get_line_data()
            res['treatment_details'].append(line_data)
        return res

    def update_process(self, queue):
        """更新就医流程"""
        m_treatment_process_line = self.env['hrp.treatment_process_line']
        total_queue_obj = self.env['hrp.total_queue']
        clinic_item_category_obj = self.env['his.clinic_item_category']
        business_obj = self.env['hrp.business']

        if queue.state in [5]:
            # 退费
            return

        # 计算code
        code = '02'

        business = business_obj.search([('name', '=', queue.business)], limit=1)
        if business:
            if business.business_category == '1':
                # 门诊
                code = '02' if queue.stage == '1' else '06'
            elif business.business_category == '2':
                # 检验
                code = '04'
            elif business.business_category == '3':
                # 检查
                code = '05'
            elif business.business_category == '4':
                # 治疗
                code = '07'
            elif business.business_category == '6':
                # 发药
                code = '08'

        line = m_treatment_process_line.search([('code', '=', code),
                                                ('queue_id', '=', queue.id),
                                                ('queue_state', '=', queue.state),
                                                ('state', '=', 'doing')], limit=1)
        if line:
            if line.queue_state == 1:
                # 待诊
                # 修改更新时间
                line.write({
                    'update_time': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                })
                # 推送就医流程
                line.send_process()
        else:
            # 查询对应总队列
            total_queues = total_queue_obj.search([('queue_id', '=', queue.id)])

            # 查询检查项目
            clinic_items = []

            for total_queue in total_queues:
                if total_queue.origin_table != 'dispose':
                    continue
                dispose = self.env['his.dispose'].search([('id', '=', total_queue.origin_id)])
                if not dispose:
                    continue
                if dispose.item_id and dispose.item_id.name not in clinic_items:
                    clinic_items.append(dispose.item_id.name)

            # 预约科室id
            reserve_department_id = False
            for clinic_item in clinic_items:
                clinic_item_category = clinic_item_category_obj.search([('name', '=', clinic_item)], limit=1)
                if not clinic_item_category:
                    continue
                reserve_department_id = clinic_item_category.department_id.id

            # 将此队列其他状态完成
            treatment_process_lines = m_treatment_process_line.search([('queue_id', '=', queue.id), ('state', '=', 'doing')])
            treatment_process_lines.write({'state': 'done'})

            # 通知手机该流程状态改变
            for tpl in treatment_process_lines:
                tpl.send_process()

            # 顺序号
            order_num = False
            if queue.queue_dispatch_ids:
                order_num = queue.queue_dispatch_ids[0].order_num_str
            elif queue.appointment_number:
                order_num = queue.appointment_number_str

            # 创建新流程
            treatment_process_line = m_treatment_process_line.create_process({
                'queue_id': queue.id,
                'partner_id': queue.partner_id.id,
                'name': dict(HrpTreatmentProcessLine.BUSINESS)[code],
                'code': code,
                'department_id': queue.department_id.id,
                'employee_id': queue.employee_id.id,
                'order_num': order_num,
                'queue_state': queue.state,
                'location': queue.department_id.location,
                'process_type': '1',
                'clinic_item': ';'.join(clinic_items) if clinic_items else False,
                'reserve_department_id': reserve_department_id
            })
            _logger.info('=====流程明细：id-%s被创建======' % treatment_process_line.id)
            # 提交，防止死锁
            self.env.cr.commit()


class HrpTreatmentProcessLine(models.Model):
    _name = 'hrp.treatment_process_line'
    _description = u'就医流程明细'
    _rec_name = 'partner_id'
    _order = 'id desc'

    BUSINESS = [('01', '挂号'), ('02', '初诊'), ('03', '缴费'), ('04', '检验'), ('05', '检查'), ('06', '回诊'), ('07', '治疗'), ('08', '取药')]

    process_id = fields.Many2one('hrp.treatment_process', '就医流程', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='process_id.partner_id')
    
    name = fields.Char('流程名称')
    code = fields.Char('流程编码')
    queue_id = fields.Many2one('hrp.queue', '队列')
    business = fields.Char('业务', related='queue_id.business')
    queue_state = fields.Selection(STATE, '队列状态')
    department_id = fields.Many2one('hr.department', '科室')
    employee_id = fields.Many2one('hr.employee', '医生')
    order_num = fields.Char('顺序号')
    location = fields.Char('位置信息')
    process_type = fields.Selection([('1', '排队'), ('2', '不排队')], '流程类型')
    message = fields.Text('信息')
    state = fields.Selection([('doing', '进行中'), ('done', '完成')], '状态', default='doing')
    duration = fields.Char('就诊持续时间')
    clinic_item = fields.Char('检查项目')
    reserve_department_id = fields.Integer('预约科室内部ID')
    pay_time = fields.Char('缴费时间')
    receipt_no = fields.Char('挂号单')
    reserve_id = fields.Integer('预约记录ID')
    update_time = fields.Datetime('更新时间', default=lambda *a: datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))



    @api.model
    def create(self, val):
        res = super(HrpTreatmentProcessLine, self).create(val)
        # 推送就医流程
        res.send_process()
        return res

    # @api.multi
    # def write(self, val):
    #     res = super(HrpTreatmentProcessLine, self).write(val)
    #     for line in self:
    #         # 推送就医流程
    #         line.send_process()
    #     return res

    def create_process(self, val):
        """创建就医流程"""
        m_treatment_process = self.env['hrp.treatment_process']

        partner_id = val.get('partner_id')
        if not partner_id:
            return

        # 当前日期
        date_now_str = (datetime.now() + timedelta(hours=8)).strftime(DEFAULT_SERVER_DATE_FORMAT)

        parent_process = m_treatment_process.search([('visit_date', '=', date_now_str), ('partner_id', '=', partner_id), ('state', '=', 'doing')], order='id desc', limit=1)
        if not parent_process:
            parent_process = m_treatment_process.create({
                'partner_id': partner_id,
                'visit_date': (datetime.now() + timedelta(hours=8)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            })
        # 父记录
        val.update({'process_id': parent_process.id})
        res = self.create(val)
        return res

    def send_process(self):
        """推送就医流程"""
        topic = self.partner_id.topic
        if not topic:
            return
        msg = {
            'action': 'send_process',
        }
        data = {
            'partner_id': self.partner_id.id,
            'visit_date': self.process_id.visit_date,
            'treatment_details': []
        }

        # 推送时间
        # send_time_str = (datetime.now() + timedelta(hours=8)).strftime('%H:%M')

        line_data = self.get_line_data()
        data['treatment_details'].append(line_data)

        msg['data'] = data

        if module.get('emqtt'):
            module['emqtt'].Emqtt.publish(topic, msg, 2)

    def get_line_data(self):
        """包装line的数据"""
        m_queue = self.env['hrp.queue']

        line_data = {
                'process_line_id': self.id,
                'time': time_to_client(self.update_time, '%Y-%m-%d %H:%M'),
                'name': self.name,
                'code': self.code,
                'business': self.business,
                'department': self.department_id.name,
                'doctor': self.queue_id.employee_id.name if self.queue_id.employee_id else '',
                'location': self.location,
                'is_queue': True if self.queue_id else False,
                'state': self.state,
                'order_num': self.order_num or '',
                'wait_count': 0,
                'wait_minutes': 0,
                'duration': self.duration,
                'clinic_item': self.clinic_item,
                'reserve_department_id': self.reserve_department_id,
                'queue_state': dict(STATE)[self.queue_state] if self.queue_id else '',
                'queue_state_code': self.queue_state if self.queue_id else 0,
                'time_point': '',
            }

        if self.code in ['01']:
            # 挂号
            # 就诊日期|时间点|预约号|医生名称
            try:
                if self.message:
                    msg_list = self.message.split('|')
                    visit_date, time_point, appointment_number, doctor = msg_list[0], msg_list[1], msg_list[2], msg_list[3]
                    line_data.update({
                        'time_point': '%s %s' % (visit_date, time_point),
                        'order_num': appointment_number,
                        'doctor': doctor
                    })
            except Exception:
                _logger.error(traceback.format_exc())

        if self.process_type == '1' and self.queue_id:
            # 排队消息

            if self.queue_id.queue_dispatch_ids:
                queue_dispatch = self.queue_id.queue_dispatch_ids[0]

                queue_data = m_queue.clean_queue(self.queue_id)

                # 计算当前等候人数
                wait_count = m_queue.get_wait_count(queue_dispatch, queue_data)

                # 计算预计等候时间
                # average_wait_time = 3
                average_wait_time = m_queue.compute_average_wait_time(self.queue_id.department_id.id)

                if self.queue_id.state == 1:
                    # 候诊状态计算等候人数和时间
                    line_data.update({
                        'wait_count': wait_count,
                        'wait_minutes': average_wait_time * wait_count,
                    })

                line_data.update({
                    'queue_state': dict(STATE)[self.queue_state],
                    'queue_state_code': self.queue_state,
                    'duration': average_wait_time,
                })
        return line_data


