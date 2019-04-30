# coding:utf-8

from odoo import models, api
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class HrpQueue(models.Model):
    _inherit = "hrp.queue"

    # def app_get_queue(self, data):
    #     """app获取队列"""
    #     m_partner = self.env['res.partner']
    #
    #     prev_partner_id = data.get('prev_partner_id')
    #     current_partner_id = data.get('current_partner_id')
    #     topic = data.get('topic')
    #
    #     # 清除之前患者topic
    #     prev_partner = m_partner.search([('id', '=', prev_partner_id)])
    #     if prev_partner:
    #         prev_partner.topic = False
    #
    #     partner = m_partner.search([('id', '=', current_partner_id)])
    #     res = {}
    #     if not partner:
    #         return res
    #     time_now = datetime.now() + timedelta(hours=8)
    #     res.update({
    #         'name': partner.name,
    #         'hospital': partner.company_id.name,
    #         'outpatient_num': partner.outpatient_num,
    #         'visit_date': time_now.strftime(DEFAULT_SERVER_DATE_FORMAT),
    #         'medical_card': '',
    #         'queue_infos': []
    #     })
    #     # 记录当前用户topic
    #     partner.topic = topic
    #     # 获取该患者的所有队列信息
    #     queues = self.search([('partner_id', '=', partner.id), ('state', 'in', [1, 2, 3, 6, 7, 8]), ('date_state', '=', '1')])
    #     if not queues:
    #         return res
    #     for queue in queues:
    #
    #         info = {
    #             'id': queue.id,
    #             'time': time_now.strftime('%M:%S'),
    #             'title': '队列信息',
    #             'business': queue.business,
    #             'department': queue.department_id.name,
    #             'location': queue.department_id.location,
    #             'wait_infos': [],
    #         }
    #
    #         for queue_dispatch in queue.queue_dispatch_ids:
    #             # 计算当前等候人数
    #             queue_data = {
    #                 'department_id': queue.department_id.id,
    #                 'business': queue.business,
    #                 'stage': queue.stage,
    #             }
    #             wait_count = self.get_wait_count(queue_dispatch, queue_data)
    #             info['wait_infos'].append({
    #                 'room_id': queue_dispatch.room_id.id,
    #                 'room_name': queue_dispatch.room_id.name,
    #                 'doctor_infos': [{'id': employee.id, 'name': employee.name} for employee in
    #                                    queue_dispatch.employee_ids],
    #                 'order_num': queue_dispatch.order_num,
    #                 'wait_count': wait_count
    #             })
    #
    #         res['queue_infos'].append(info)
    #     return res

