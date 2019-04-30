# coding: utf-8

from functools import wraps
from odoo.http import request
from odoo import http
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT, config
from ..models.hrp_mqtt import send_msg
from ..models.hrp_const import time_to_client

import logging
import json
import os
import re

_logger = logging.getLogger(__name__)


def interface_wraps(func):
    """接口包装"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if func.func_name == 'send_log':
            _logger.info(u'%s返回数据:忽略', func.func_name)
        else:
            _logger.info(u'%s收到数据:%s', func.func_name, json.dumps(request.jsonrequest, ensure_ascii=False, encoding='utf8', indent=True))

        result = func(self, *args, **kwargs)
        if func.func_name != 'get_queue':
            _logger.info(u'%s返回数据:%s', func.func_name, json.dumps(result, ensure_ascii=False, encoding='utf8', indent=True))
        else:
            _logger.info(u'%s返回数据:忽略', func.func_name)

        return result

    return wrapper


class SelfInterface(http.Controller):
    """自助端接口"""
    @http.route('/self/start', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def self_start(self):
        """设备运行"""
        equipment_obj = request.env['hrp.equipment'].sudo() # 设备

        # 设备编号
        code = request.jsonrequest.get('code')
        equipment = equipment_obj.search([('code', '=', code)])
        if not equipment:
            return {
                'state': 0,
                'desc': '设备号错误'
            }
        # 如果设备在线且mac不一致
        if equipment.online and equipment.ip != request.jsonrequest.get('ip'):
            return {
                'state': 0,
                'desc': '设备已在线'
            }

        # 设备类型
        type_code = request.jsonrequest.get('type_code')
        equipment_type = request.env['hrp.equipment_type'].search([('code', '=', type_code)])
        if not equipment_type:
            return {
                'state': 0,
                'desc': '设备类型不存在'
            }
        # 上传设备信息
        equipment.write({
            'ip': request.jsonrequest.get('ip'),
            'equipment_type_id': equipment_type.id,
            'mac': request.jsonrequest.get('mac'),
            'version': request.jsonrequest.get('version'),
            'online': 1,
            'state': request.jsonrequest.get('state', '1'),
        })

        # 记录程序日志
        log_datetime = request.jsonrequest.get('log_datetime')
        if not log_datetime:
            log_datetime = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        else:
            log_datetime = (datetime.strptime(log_datetime, DEFAULT_SERVER_DATETIME_FORMAT) - timedelta(hours=8)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        request.env['hrp.equipment.log'].create({
            'equipment_id': equipment.id,
            'user_id': request.session.uid if request.session.uid else False,
            'log_datetime': log_datetime,
            'log_type': '2',
            'log_content': '设备运行'
        })

        # 返回数据
        result = {
            'state': 1,
            'equipment_info': {
                'equipment_id': equipment.id, # 设备ID
                'equipment_code': equipment.code, # 设备编号
                'params': equipment.get_equipment_parameter(),  # 设备参数
                'businesses': [business.name for business in equipment.business_ids]
            },
            'emqtt_config': {
                'mqtt_id': config['mqtt_ip'],
                'mqtt_port': config['mqtt_port'],
                'mqtt_username': config['mqtt_username'],
                'mqtt_password': config['mqtt_password']
            },
            'ads': self.get_ad(equipment)
        }

        return result

    @staticmethod
    def get_ad(equipment):
        """返回广告"""
        return [
            {
                'id': template.id,
                'type': template.type,  # 类型
                'interval': template.interval,  # 切换时间间隔
                'ads': [
                    {
                        'id': line.id,
                        'write_date': (datetime.strptime(line.advertisement_id.write_date, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=8)).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'type': line.advertisement_id.type,  # 类型
                        'url': '/web/image/hrp.advertisement/%s/image' % line.advertisement_id.id if line.advertisement_id.type == 'image' else '/web/content/hrp.advertisement/%s/file' % line.advertisement_id.id,
                    } for line in template.template_line_ids],
            } for template in equipment.advertisement_template_ids]

    @http.route('/self/queue_state_change', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def queue_state_change(self):
        """签到，叫号，过号，完成"""
        equipment = request.env['hrp.equipment'].sudo().search([('code', '=', request.jsonrequest.get('code'))])
        if not equipment:
            return {'state': 0, 'desc': '设备号错误'}
        result = request.env['hrp.queue'].sudo().queue_state_change(equipment.user_id, request.jsonrequest)
        return result

    @http.route('/self/get_equipment_info', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_equipment_info(self):
        """获取设备信息"""
        code = request.jsonrequest.get('code')

        equipment = request.env['hrp.equipment'].sudo().search([('code', '=', code)])
        if not equipment:
            return {'state': 0, 'desc': '设备号错误'}

        # 获取设备信息
        result = equipment.get_equipment_info_by_equipment()
        return {'state': 1, 'result': result}

    @http.route('/self/user_login', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def user_login(self):
        """用户登陆"""
        m_equipment = request.env['hrp.equipment'].sudo()
        m_equipment_registered_type = request.env['hrp.equipment_registered_type'].sudo()

        def employee_dept_right():
            equip_department_ids = [d.department_id.id for d in equipment.department_info_ids]
            if not equip_department_ids:
                return False, {'state': 0, 'desc': '设备未设置科室'}
            if not employee:
                return False, {'state': 0, 'desc': '用户未关联员工'}
            if not employee.department_ids:
                return False, {'state': 0, 'desc': '员工未设置科室'}
            for e_dept in employee.department_ids:
                if e_dept.id in equip_department_ids:
                    return True, {}
            return False, {'state': 0, 'desc': '您不能登陆该科室'}

        # 验证设备
        code = request.jsonrequest.get('code')
        equipment = m_equipment.search([('code', '=', code)])
        if not equipment:
            return {'state': 0, 'desc': '设备号错误'}
        # 用户名，密码
        username, password = request.jsonrequest.get('username'), request.jsonrequest.get('password')
        # 验证用户
        uid = request.session.authenticate(request.session.db, username, password)

        if not uid:
            return {'state': 0, 'desc': '用户名或密码错误'}
        # 用户是否已登陆其他设备
        equipments = m_equipment.search([('code', '!=', code), ('user_id', '=', uid), ('online', '=', True)])
        if equipments:
            return {'state': 0, 'desc': '用户已经登陆'}

        employee = request.env['res.users'].sudo().browse(uid).employee_ids[0] if request.env['res.users'].sudo().browse(uid).employee_ids else False

        # 验证医生的科室与设备科室是否一致
        res = employee_dept_right()
        if not res[0]:
            return res[1]

        # 修改设备状态
        equipment.write({
            'user_id': uid,
            'online': True,
        })
        # 记录员工号类
        equipment_registered_type = m_equipment_registered_type.sudo().is_equipment_registered_type_exit(equipment)
        if not equipment_registered_type:
            # 创建
            m_equipment_registered_type.create({'equipment_id': equipment.id, 'employee_id': employee.id, 'registered_type_ids': [(6, 0, employee.registered_type_ids.ids)]})

        # 记录日志
        request.env['hrp.equipment.log'].create({
            'equipment_id': equipment.id,
            'user_id': uid,
            'log_datetime': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'log_type': '2',
            'log_content': '用户登陆'
        })
        # 执行计划任务（以保证医生登陆马上能获取到信息）
        # request.env['hrp.total_queue'].sudo().hrp_queue_cron()
        # queue_cron = request.env['ir.model.data'].sudo().xmlid_to_object('hrp_queue.queue_cron')
        # queue_cron.method_direct_trigger()

        # 发送消息通知其他设备
        if equipment.equipment_type_id and equipment.equipment_type_id.code == 'DCT':

            equipment.emplinfo_to_relation_equip(action='user_login')
            # empl_info = equipment.get_emplp_by_equip()
            # if empl_info and equipment.department_info_ids:
            #     for dept_ino in equipment.department_info_ids:
            #         send_msg(dept_ino.department_id.pinyin, {'action': 'user_login', 'msg': empl_info})

        return {'state': 1, 'desc': '登陆成功'}

    @http.route('/self/login_out', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def login_out(self):
        """设备退出"""
        m_equipment = request.env['hrp.equipment'].sudo()
        # 验证设备
        code = request.jsonrequest.get('code')
        equipment = m_equipment.search([('code', '=', code)])
        user = equipment.user_id if equipment and equipment.user_id else False
        if equipment:
            # 修改状态
            equipment.write({
                'user_id': False,
                'online': False,
            })
            # 记录日志
            request.env['hrp.equipment.log'].create({
                'equipment_id': equipment.id,
                'user_id': user.id if user else False,
                'log_datetime': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'log_type': '2',
                'log_content': '设备退出'
            })
            # 发送消息通知其他设备
            if equipment.equipment_type_id and equipment.equipment_type_id.code == 'DCT':
                if user and user.employee_ids:
                    for dept_info in equipment.department_info_ids:
                        send_msg(dept_info.department_id.pinyin, {'action': 'login_out', 'msg': {'employee_id': user.employee_ids[0].id}})
        return {'state': 1}

    @http.route('/self/get_queue', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_queue(self):
        """获取队列"""
        m_equipment = request.env['hrp.equipment']
        m_queue = request.env['hrp.queue'].sudo()

        code = request.jsonrequest.get('code')
        # 获取设备
        equipment = m_equipment.search([('code', '=', code)])
        if not equipment:
            return {'state': 0, 'desc': '设备号错误'}
        businesses = [business.name for business in equipment.business_ids]
        department_ids = [department_info.department_id.id for department_info in equipment.department_info_ids]
        queues = m_queue.search(
            [('business', 'in', businesses), ('department_id', 'in', department_ids), ('date_state', '=', '1')])
        results = []

        queues = list(queues)
        queues.sort(key=lambda q: q.queue_dispatch_ids[0].order_num if q.queue_dispatch_ids else 0)

        for queue in queues:
            data = m_queue.clean_queue(queue)
            if not data:
                continue
            results.append(data)

        return {'state': 1, 'result': results}

    @http.route('/self/send_log', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def send_log(self):
        """日志传送
            equipment_id:设备ID
            log_file_name:日志文件名称
            log_content:日志内容
        """
        # 客户端日志文件路径
        folder = ['', 'var', 'log', 'self_equipment']
        path = os.path.sep.join(folder)
        if not os.path.exists(path):
            os.mkdir(path)

        # 创建设备目录
        folder.append(str(request.jsonrequest['code']))
        path = os.path.sep.join(folder)
        if not os.path.exists(path):
            os.mkdir(path)

        # 文件如果存在，则删除
        folder.append(request.jsonrequest['log_file_name'])
        filename = os.path.sep.join(folder)
        if os.path.exists(filename):
            os.remove(filename)

        # 写入文件内容
        log_file = open(filename, 'w')
        log_file.write(request.jsonrequest['log_content'].encode('utf8'))
        log_file.close()

        return {'state': 1}

    @http.route('/self/logging', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def logging(self):
        """上传日志"""
        m_equipment = request.env['hrp.equipment']

        code = request.jsonrequest.get('code')
        equipment = m_equipment.search([('code', '=', code)])
        if not equipment:
            return {'state': 0, 'desc': '设备号错误'}
        log_datetime = request.jsonrequest.get('log_datetime')
        try:
            log_datetime = (
            datetime.strptime(log_datetime, DEFAULT_SERVER_DATETIME_FORMAT) - timedelta(hours=8)).strftime(
                DEFAULT_SERVER_DATETIME_FORMAT)
        except Exception:
            _logger.error('日志时间格式错误')
            log_datetime = False
        request.env['hrp.equipment.log'].create({
            'equipment_id': equipment.id,
            'user_id': equipment.user_id.id if equipment.user_id else False,
            'log_type': '2',
            'log_datetime': log_datetime or False,
            'log_content': request.jsonrequest.get('log_content')
        })
        return {'state': 1}

    @http.route('/self/keeplive', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def keeplive(self):
        """心跳检查"""
        return {'state': 1}

    @http.route('/self/get_empl_info_by_equip', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_empl_info_by_equip(self):
        """获取设备对应的医生信息"""
        m_equipment = request.env['hrp.equipment'].sudo()

        res = []
        code = request.jsonrequest.get('code')
        equipment = m_equipment.search([('code', '=', code)])
        if not equipment:
            return {'state': 0, 'desc': '设备号错误'}

        equipments = m_equipment.search([('online', '=', True), ('user_id', '!=', False), ('equipment_type_id.code', '=', 'DCT')])
        for e in equipments:
            result = False
            u = e.user_id
            # 过滤不是医生的用户
            if not u.employee_ids:
                continue
            for department_info in e.department_info_ids:
                for info in equipment.department_info_ids:
                    if department_info.department_id.id != info.department_id.id:
                        continue
                    if not info.room_ids or not department_info.room_ids:
                        result = True
                    elif set(department_info.room_ids).issubset(set(info.room_ids)):
                        result = True
            if not result:
                continue
            empl_info = e.get_emplp_by_equip()
            if empl_info:
                res.append(empl_info)
        return {'state': 1, 'result': res}

    @http.route('/self/get_parameters', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_parameters(self):
        """获取参数"""
        equipment_obj = request.env['hrp.equipment'].sudo()  # 设备

        # 设备编号
        code = request.jsonrequest.get('code')
        equipment = equipment_obj.search([('code', '=', code)])
        if not equipment:
            return {'state': 0, 'desc': '设备号错误'}

        return {
            'state': 1,
            'params': equipment.get_equipment_parameter()
        }

    @http.route('/self/get_ads', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_ads(self):
        """获取参数"""
        equipment_obj = request.env['hrp.equipment'].sudo()  # 设备

        # 设备编号
        code = request.jsonrequest.get('code')
        equipment = equipment_obj.search([('code', '=', code)])
        if not equipment:
            return {'state': 0, 'desc': '设备号错误'}

        return {
            'state': 1,
            'ads': self.get_ad(equipment)
        }

    @http.route('/self/set_equip_state', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def set_equip_state(self):
        equipment_obj = request.env['hrp.equipment'].sudo()  # 设备

        # 设备编号
        code = request.jsonrequest.get('code')
        equipment = equipment_obj.search([('code', '=', code)])
        if not equipment:
            return {'state': 0, 'desc': '设备号错误'}
        equipment.write({'state': request.jsonrequest.get('state', '1')})
        # 发送消息通知其他设备
        for dept_ino in equipment.department_info_ids:
            send_msg(dept_ino.department_id.pinyin, {'action': 'update_equip_state', 'msg': {'equpment_id': equipment.id, 'state': equipment.state}})
        return {'state': 1}

    @http.route('/self/update_equipment_registered_types', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def update_equipment_registered_types(self):
        equipment_obj = request.env['hrp.equipment'].sudo()  # 设备
        # m_equipment_registered_type = request.env['hrp.equipment_registered_type'].sudo()
        m_registered_type = request.env['hrp.registered.type'].sudo()

        code = request.jsonrequest.get('code')
        registered_type_names = request.jsonrequest.get('registered_types', [])

        equipment = equipment_obj.search([('code', '=', code)])
        if not equipment:
            return {'state': 0, 'desc': '设备号错误'}
        if not equipment.user_id:
            return {'state': 0, 'desc': '当前没有用户登录'}

        employee = equipment.user_id.employee_ids[0] if equipment.user_id.employee_ids else False

        if not employee:
            return {'state': 0, 'desc': '用户没有对应员工'}
        registered_types = m_registered_type.search([('name', 'in', registered_type_names)])

        # equipment_registered_type = m_equipment_registered_type.is_equipment_registered_type_exit(equipment)
        # if not equipment_registered_type:
        #     # 创建
        #     m_equipment_registered_type.create({
        #         'equipment_id': equipment.id,
        #         'employee_id': employee.id,
        #         'registered_type_ids': [(6, 0, registered_types.ids)]
        #     })
        # else:
        #     equipment_registered_type.write({'registered_type_ids': [(6, 0, registered_types.ids)]})

        if registered_type_names and not registered_types:
            return {'state': 0, 'desc': '所选择的号类不存在'}

        equipment.write({'registered_type_ids': [(6, 0, registered_types.ids)]})

        # 医生通知对应设备
        equipment.emplinfo_to_relation_equip(action='update_registered_type')

        return {'state': 1, 'desc': '修改成功'}

    # 不关联号源取号
    # @http.route('/self/get_free_num_info', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    # @interface_wraps
    # def get_free_num_info(self):
    #     """获取免费号信息"""
    #     business_obj = request.env['hrp.business'].sudo()
    #     queue_obj = request.env['hrp.queue'].sudo()
    #
    #     business_name = request.jsonrequest['business']
    #
    #     time_now = datetime.now()
    #     today = (time_now + timedelta(hours=8)).strftime(DEFAULT_SERVER_DATE_FORMAT)
    #
    #     # 计算科室
    #     business = business_obj.search([('name', '=', business_name)])
    #     if not business:
    #         return {'state': 0, 'desc': '业务错误！'}
    #
    #     department_id = business.business_department_ids[0].department_id.id \
    #         if business.business_department_ids and business.business_department_ids[0].department_id else False
    #
    #     # 计算当前等候人数
    #     args = [('date_state', '=', '1'), ('department_id', '=', department_id), ('state', 'in', [-1, 1, 2])]
    #
    #     queues = queue_obj.search(args)
    #
    #     wait_count = len(queues)
    #
    #     # 平均等待时间
    #     average_wait_time = queue_obj.compute_average_wait_time(department_id)
    #     wait_time = wait_count * average_wait_time
    #
    #     # 返回信息
    #     res = {
    #         'register_source_id': 0,
    #         'department': business.business_department_ids[0].department_id.name,
    #         'doctor': '',
    #         'business': business_name,
    #         'visit_time': '',
    #         'wait_count': wait_count,
    #         'wait_time': wait_time,
    #     }
    #
    #     return {'state': 1, 'data': res}
    #
    # @http.route('/self/get_free_num', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    # @interface_wraps
    # def get_free_num(self):
    #     """获取免费号"""
    #     total_queue_obj = request.env['hrp.total_queue'].sudo()
    #     partner_obj = request.env['res.partner'].sudo()
    #     queue_obj = request.env['hrp.queue'].sudo()
    #     equipment_obj = request.env['hrp.equipment'].sudo()
    #     business_department_obj = request.env['hrp.business_department'].sudo()
    #
    #     business_name = request.jsonrequest['business']
    #
    #     def get_partner():
    #         tq = total_queue_obj.search([('date_state', '=', '1'), ('origin', '=', '5')], order='id desc', limit=1)
    #         if not tq:
    #             name = '免001'
    #         else:
    #             # name = '免%03d' % (int(tq.partner_id.name[3:]) + 1)
    #             name = '免%03d' % (int(re.findall(r"\d+", tq.partner_id.name)[0]) + 1)
    #         p = partner_obj.search([('name', '=', name)], limit=1)
    #         if not p:
    #             p = partner_obj.create({
    #                 'name': name,
    #                 'outpatient_num': datetime.now().strftime('%y%m%d%H%M%S'),
    #                 'is_patient': True
    #             })
    #         return p
    #
    #     # 获取患者
    #     partner = get_partner()
    #
    #     time_now = datetime.now()
    #
    #     # 根据business获取科室
    #     business_department = business_department_obj.search([('business_id.name', '=', business_name)], limit=1)
    #     if not business_department:
    #         return {'state': 0, 'desc': '业务错误'}
    #
    #     # 等候人数
    #     args = [('date_state', '=', '1'), ('department_id', '=', business_department.department_id.id),
    #             ('state', 'in', [-1, 1, 2])]
    #
    #     queues = queue_obj.search(args)
    #     count = len(queues)
    #
    #     # 平均等待时间
    #     average_wait_time = queue_obj.compute_average_wait_time(business_department.department_id.id)
    #     wait_time = count * average_wait_time
    #
    #     # 插入队列
    #     total_queue = total_queue_obj.create({
    #         'partner_id': partner.id,
    #         'outpatient_num': partner.outpatient_num,
    #         'business': business_name,
    #         'department_id': business_department.department_id.id,
    #         'origin': '5',
    #         'register_type': '公卫号',
    #         'enqueue_datetime': time_now.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
    #         'state': False,
    #     })
    #
    #     # 返回信息
    #
    #     # 位置信息
    #     dept_position = total_queue.department_id.location or ''
    #
    #     if total_queue.employee_id:
    #         # 挂号到医生
    #         doc_equipment = equipment_obj.search(
    #             [('employee_id', '=', total_queue.employee_id.id), ('online', '=', True)], limit=1)
    #         if doc_equipment and doc_equipment.department_info_ids and doc_equipment.department_info_ids[0].room_ids:
    #             dept_position = doc_equipment.department_info_ids[0].room_ids[0].location or ''
    #
    #     res = {
    #         'dept_position': dept_position,
    #         'clinic_type': total_queue.register_type,
    #         'department': total_queue.department_id.name,
    #         'doctor': '',
    #         'outpatient_num': partner.outpatient_num,
    #         'register_time': time_to_client(total_queue.enqueue_datetime),
    #         'visit_date': total_queue.visit_date,
    #         'name': partner.name,
    #         'business': business_name,
    #         'visit_time': '',
    #         'count': count,
    #         'wait_time': wait_time,
    #         'appointment_number': total_queue.appointment_number_str if total_queue.appointment_number_str else '',
    #     }
    #
    #     return {'state': 1, 'data': res}
    #
    # @http.route('/self/cancel_free_num', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    # @interface_wraps
    # def cancel_free_num(self):
    #     """取消免费号"""
    #     return {'state': 1}

    # 关联号源取号
    @http.route('/self/get_free_num_info', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_free_num_info(self):
        """获取免费号信息"""
        register_source_obj = request.env['his.register_source'].sudo()
        business_obj = request.env['hrp.business'].sudo()
        queue_obj = request.env['hrp.queue'].sudo()

        business_name = request.jsonrequest['business']

        time_now = datetime.now()
        today = (time_now + timedelta(hours=8)).strftime(DEFAULT_SERVER_DATE_FORMAT)

        # 计算科室
        business = business_obj.search([('name', '=', business_name)])
        if not business:
            return {'state': 0, 'desc': '业务错误！'}

        department_id = business.business_department_ids[0].department_id.id \
            if business.business_department_ids and business.business_department_ids[0].department_id else False

        # 获取号源(当天，同科室，班次未过期，班次未停诊, 号源未过期， 可预约)
        register_source = register_source_obj.search([('date', '=', today),
                                                      ('time_point_name', '>=', (time_now+timedelta(hours=8)).strftime('%H:%M')),
                                                      ('department_id', '=', department_id),
                                                      ('shift_id.expired', '=', False),
                                                      ('shift_id.is_stop', '=', False),
                                                      ('state', '=', '0')], order='time_point_name', limit=1)
        if not register_source:
            return {'state': 0, 'desc': '已停诊'}

        # 锁定号源
        if not register_source_obj.lock_register_source(register_source.id)['data']['state']:
            # 失败
            return {'state': 0, 'desc': '请重试'}

        # 计算当前等候人数
        args = [('date_state', '=', '1'), ('department_id', '=', department_id), ('state', 'in', [-1, 1, 2])]
        if register_source.employee_id:
            args += [('employee_id', '=', register_source.employee_id.id)]

        queues = queue_obj.search(args)

        wait_count = len(queues)

        # 平均等待时间
        average_wait_time = queue_obj.compute_average_wait_time(department_id)
        wait_time = wait_count * average_wait_time

        # 返回信息
        res = {
            'register_source_id': register_source.id,
            'department': business.business_department_ids[0].department_id.name,
            'doctor': register_source.employee_id.name if register_source.employee_id else '',
            'business': business_name,
            'visit_time': register_source.time_point_name,
            'wait_count': wait_count,
            'wait_time': wait_time,
        }

        return {'state': 1, 'data': res}


    @http.route('/self/get_free_num', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_free_num(self):
        """获取免费号"""
        total_queue_obj = request.env['hrp.total_queue'].sudo()
        partner_obj = request.env['res.partner'].sudo()
        queue_obj = request.env['hrp.queue'].sudo()
        register_source_obj = request.env['his.register_source'].sudo()
        register_plan_line_obj = request.env['his.register_plan_line'].sudo()
        equipment_obj = request.env['hrp.equipment'].sudo()
        # business_department_obj = request.env['hrp.business_department'].sudo()

        register_source_id = request.jsonrequest['register_source_id']
        business_name = request.jsonrequest['business']

        def get_partner():
            tq = total_queue_obj.search([('date_state', '=', '1'), ('origin', '=', '5')], order='id desc', limit=1)
            if not tq:
                name = '免001'
            else:
                # name = '免%03d' % (int(tq.partner_id.name[3:]) + 1)
                name = '免%03d' % (int(re.findall(r"\d+", tq.partner_id.name)[0]) + 1)
            p = partner_obj.search([('name', '=', name)], limit=1)
            if not p:
                p = partner_obj.create({
                    'name': name,
                    'outpatient_num': datetime.now().strftime('%y%m%d%H%M%S'),
                    'is_patient': True
                })
            return p

        # 获取患者
        partner = get_partner()

        # 号源
        register_source = register_source_obj.search([('id', '=', register_source_id), ('state', '=', '2')])

        if not register_source:
            return {'state': 0, 'desc': '号源错误'}

        time_now = datetime.now()

        # 修改号源状态
        register_source.state = '1'

        # 预约时间
        appointment_time_str = '{} {}'.format(register_source.date, register_source.time_point_name)
        appointment_time = datetime.strptime(appointment_time_str, '%Y-%m-%d %H:%M') - timedelta(hours=8)

        # 队列计划
        register_plan_line = register_plan_line_obj.search([('register_plan_id.schedule_id', '=', register_source.shift_id.schedule_id.id),
                                                            ('time_point_name', '=', register_source.time_point_name)], limit=1)
        # 预约号
        medical_sort = False
        if register_plan_line:
            # 修改队列计划
            register_plan_line.write({
                'partner_id': partner.id,
                'source': 'manual',
                'register_time': time_now.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            })
            medical_sort = register_plan_line.medical_sort

        # 等候人数
        args = [('date_state', '=', '1'), ('department_id', '=', register_source.department_id.id),
                ('state', 'in', [-1, 1, 2])]
        if register_source.employee_id:
            args += [('employee_id', '=', register_source.employee_id.id)]

        queues = queue_obj.search(args)
        count = len(queues)

        # 平均等待时间
        average_wait_time = queue_obj.compute_average_wait_time(register_source.department_id.id)
        wait_time = count * average_wait_time

        # 插入队列
        total_queue = total_queue_obj.create({
            'partner_id': partner.id,
            'outpatient_num': partner.outpatient_num,
            'business': business_name,
            'department_id': register_source.department_id.id,
            'employee_id': register_source.employee_id.id,
            'origin': '5',
            'register_type': '公卫号',
            'enqueue_datetime': time_now.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'state': False,
            'appointment_time': appointment_time,
            'appointment_number': medical_sort
        })

        # 返回信息

        # 位置信息
        dept_position = total_queue.department_id.location or ''

        if total_queue.employee_id:
            # 挂号到医生
            doc_equipment = equipment_obj.search([('employee_id', '=', total_queue.employee_id.id), ('online', '=', True)], limit=1)
            if doc_equipment and doc_equipment.department_info_ids and doc_equipment.department_info_ids[0].room_ids:
                dept_position = doc_equipment.department_info_ids[0].room_ids[0].location or ''

        res = {
            'dept_position': dept_position,
            'clinic_type': total_queue.register_type,
            'department': total_queue.department_id.name,
            'doctor': register_source.employee_id.name if register_source.employee_id else '',
            'outpatient_num': partner.outpatient_num,
            'register_time': time_to_client(total_queue.enqueue_datetime),
            'visit_date': total_queue.visit_date,
            'name': partner.name,
            'business': business_name,
            'visit_time': register_source.time_point_name,
            'count': count,
            'wait_time': wait_time,
            'appointment_number': total_queue.appointment_number_str if total_queue.appointment_number_str else '',
        }

        return {'state': 1, 'data': res}


    @http.route('/self/cancel_free_num', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def cancel_free_num(self):
        """取消免费号"""
        register_source_obj = request.env['his.register_source'].sudo()

        register_source_id = request.jsonrequest['register_source_id']

        # 号源
        register_source = register_source_obj.search([('id', '=', register_source_id)])

        if not register_source:
            return {'state': 0, 'desc': '号源错误'}

        if register_source.state == '2':
            # 解锁号源
            register_source.state = '0'

        return {'state': 1}


    @http.route('/self/search_registered_patient', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def search_registered_patient(self):
        """查询当天挂号患者"""
        total_queue_obj = request.env['hrp.total_queue'].sudo()

        key = request.jsonrequest['key']

        # 当天挂号的数据
        total_queues = total_queue_obj.search([('date_state', '=', '1'),
                                               ('business', '=', u'就诊'),
                                               '|', ('partner_id.name', 'ilike', key),
                                               '|', ('spell', 'ilike', key),
                                               '|', ('outpatient_num', 'ilike', key), ('partner_id.card_no', 'ilike', key)])
        res = []

        for total_queue in total_queues:
            res.append({
                'total_queue_id': total_queue.id,
                'name': total_queue.partner_id.name,
                'outpatient_num': total_queue.outpatient_num,
                'card_no': total_queue.partner_id.card_no or '',
                'spell': total_queue.spell,
                'department': total_queue.department_id.name or '',
                'doctor': total_queue.employee_id.name or '',
                'register_type': total_queue.register_type or '',
                'register_time': time_to_client(total_queue.enqueue_datetime),
                'appointment_number_str': total_queue.appointment_number_str or '',
                'appointment_time': time_to_client(total_queue.appointment_time) or '',
                'operator_code': total_queue.operator_code or '',
            })

        return {'state': 1, 'data': res}


    @http.route('/self/reprint_register_info', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def reprint_register_info(self):
        """重新打印挂号信息"""
        total_queue_obj = request.env['hrp.total_queue'].sudo()
        queue_obj = request.env['hrp.queue'].sudo()
        equipment_obj = request.env['hrp.equipment'].sudo()

        total_queue_id = request.jsonrequest['total_queue_id']

        # 当天挂号的数据
        total_queue = total_queue_obj.search([('id', '=', total_queue_id)])

        if not total_queue:
            return {'state': 0, 'desc': '数据未找到'}

        location = ''
        # 一定挂在医生头上
        if total_queue.employee_id:
            # 等待人数
            queues = queue_obj.search([('date_state', '=', '1'), ('department_id', '=', total_queue.department_id.id),
                                       ('employee_id', '=', total_queue.employee_id.id), ('state', 'in', [-1, 1, 2])])

            # 医生坐诊诊室位置
            doc_equipment = equipment_obj.search([('employee_id', '=', total_queue.employee_id.id), ('online', '=', True)],
                                                 limit=1)
            if doc_equipment and doc_equipment.department_info_ids and doc_equipment.department_info_ids[0].room_ids:
                location = doc_equipment.department_info_ids[0].room_ids[0].location or ''
        else:
            queues = queue_obj.search([('date_state', '=', '1'), ('department_id', '=', total_queue.department_id.id),
                                       ('state', 'in', [-1, 1, 2])])

        wait_count = len(queues)

        # 平均等待时间
        average_wait_time = queue_obj.compute_average_wait_time(total_queue.department_id.id)

        wait_time = wait_count * average_wait_time

        gender = ''
        if total_queue.partner_id.gender == 'male':
            gender = u'男'
        elif total_queue.partner_id.gender == 'female':
            gender = u'女'

        # 打印的信息
        res = {
            'name': total_queue.partner_id.name,
            'gender': gender,
            'age': total_queue.partner_id.age or '',
            'register_time': time_to_client(total_queue.enqueue_datetime),
            'visit_date': total_queue.visit_date,
            'outpatient_num': total_queue.outpatient_num or '',
            'card_no': total_queue.partner_id.card_no or '',
            'department': total_queue.department_id.name,
            'register_type': total_queue.register_type or '',
            'doctor': total_queue.employee_id.name or '',
            'doctor_title': total_queue.employee_id.title or '',
            'location': location,
            'appointment_number': total_queue.appointment_number_str or '',
            'wait_count': wait_count,
            'wait_time': wait_time,
        }

        return {'state': 1, 'data': res}

    @http.route('/self/get_dispose', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_dispose(self):
        """获取医嘱"""
        dispose_obj = request.env['his.dispose'].sudo()
        outpatient_fee_obj = request.env['his.outpatient_fee'].sudo()

        partner_id = request.jsonrequest['partner_id']
        department_id = request.jsonrequest['department_id']

        disposes = dispose_obj.search([('partner_id', '=', partner_id), ('department_id', '=', department_id)])

        dispose_infos = []

        for dispose in disposes:
            res = {
                'his_id': dispose.his_id,
                'partner_id': dispose.partner_id.id,
                'clinic_type': dispose.clinic_type,   # 诊疗类别
                'part': dispose.part,   # 诊疗部位
                'department_id': dispose.department_id.id,
                'dispose_datetime': dispose.dispose_datetime,
                'amount_total': dispose.amount_total,   # 给予总量
                'frequency': dispose.frequency,  # 频率次数
                'frequency_interval': dispose.frequency_interval,  # 频率间隔
                'interval_unit': dispose.interval_unit,  # 间隔单位
                'days': dispose.days,  # 天数
                'relation_dispose_id': dispose.relation_dispose_id,  # 相关ID
                'item_id': dispose.item_id.id,  # 诊疗项目ID
                'item': dispose.item_id.name,   # 诊疗项目
                'method': dispose.method,   # 检查方法
                'origin': dispose.origin,   # 病人来源
                'receipt_no': dispose.receipt_no,   # 挂号单
                'paid': True if outpatient_fee_obj.search([('dispose_id', '=', dispose.id)]) else False,    # 是否缴费
            }
            dispose_infos.append(res)
        return {'state': 1, 'data': dispose_infos}


    @http.route('/app/test', type='json', auth="public", methods=['POST'], cors='*',
                csrf=False)
    @interface_wraps
    def test(self):
        """测试"""
        data = request.jsonrequest.get('data')
        res = request.env['hrp.treatment_process'].sudo().get_process(data)
        return res


class HrpScheduleController(http.Controller):
    """排班"""
    @http.route('/schedule/edit', type='http', auth='public', website=True)
    def edit(self):
        results = request.env['hrp.schedule_manage'].get_schedule_results()
        return request.render('hrp_queue.schedule_results', results)