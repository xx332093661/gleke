# -*- encoding:utf-8 -*-
import json
import logging
import traceback
import urllib
import urllib2

from odoo import api
from emqtt_business_proccess import EmqttBusinessProcess
from odoo.tools import config

_logger = logging.getLogger(__name__)


class EmqttBusinessProcessInherit(EmqttBusinessProcess):
    """Emqtt业务处理"""

    @api.model
    def add_patient(self, message):
        """更新患者信息"""
        patient_obj = self.env['hrp.patient']

        data = json.loads(message.payload)

        partner_id = data['partner_id'] # 就诊人ID
        internal_id = data['internal_id'] # 内部ID
        card_no = data.get('card_no')   # 就诊卡

        company = self.env['res.company'].search([('topic', '=', message.source_topic)], limit=1)

        patient_obj.create({
            'partner_id': partner_id,
            'card_no': card_no,
            'internal_id': internal_id,
            'company_id': company.id,
        })

        try:
            # 向APP发送患者内部ID
            # 当前就诊人对应的关系对应的用户
            partner = self.env['his.partner_relationship'].search([('partner_id', '=', partner_id)]).parent_id

            msg = {
                'action': 'add_patient',
                'data': {
                    'partner_id': partner_id, # 就诊人ID
                    'company_id': self.env['res.company'].search([('topic', '=', message.source_topic)]).id,  # 医院ID
                    'internal_id': internal_id, # 内部ID
                    'card_no': card_no, # 就诊卡
                }
            }
            self.publish(partner.phone, msg)
        except:
            _logger.error(traceback.format_exc())



    @api.model
    def add_doctor(self, message):
        """添加医生信息"""
        employee_obj = self.env['hr.employee']
        partner_obj = self.env['res.partner']

        data = json.loads(message.payload)

        partner_id = data['partner_id']
        internal_id = data['internal_id']

        company = self.env['res.company'].search([('topic', '=', message.source_topic)], limit=1)

        employee = employee_obj.search([('company_id', '=', company.id), ('internal_id', '=', internal_id)], limit=1)
        if not employee:
            return
        partner = partner_obj.search([('id', '=', partner_id)])
        if not partner:
            return
        partner.write({'employee_ids': [(4, employee.id)]})


    @api.model
    def register_done(self, message):
        """挂号完成"""

        refund_apply_obj = self.env['his.refund_apply']  # 退款申请

        data = json.loads(message.payload)

        appointment_record_data = data['appointment_record'] # 预约信息
        reserve_record = self.env['his.reserve_record'].browse(appointment_record_data['id'])  # 预约记录

        # 修改预约挂号记录信息
        reserve_record.write({
            'internal_id': appointment_record_data['internal_id'],
            'reserve_sort': appointment_record_data['reserve_sort'] # 顺序号
        })

        order = reserve_record.order_id
        # 修改订单信息
        order.internal_id = data['order_internal_id'] # 订单内部ID

        # 修改支付结果信息
        if order.pay_method == 'weixin':
            order.weixin_pay_ids[0].internal_id = data['pay_record_internal_id'] # 支付记录内部ID

        if order.pay_method == 'alipay':
            order.alipay_ids[0].internal_id = data['pay_record_internal_id'] # 支付记录内部ID

        # 内网处理挂号失败
        if data.get('refund_apply_internal_id'):
            # 创建退款申请
            res = {
                'partner_id': order.partner_id.id,
                'visit_partner_id': order.visit_partner_id.id,
                'pay_method': order.pay_method,
                'amount_total': order.amount_total,
                'order_ids': [(6, 0, [order.id])],
                'state': 'draft',
                'company_id': order.company_id.id,
                'internal_id': data['refund_apply_internal_id'],
                'reason': '创建挂号发生错误，号源被占用'
            }
            if order.pay_method == 'weixin':
                res.update({
                    'weixin_pay_ids': [(6, 0, [weixin_pay.id for weixin_pay in order.weixin_pay_ids])]
                })
            if order.pay_method == 'alipay':
                res.update({
                    'alipay_ids': [(6, 0, [alipay.id for alipay in order.alipay_ids])]
                })
            refund_apply_obj.create(res)

            # 修改预约记录状态
            reserve_record.state = 'draft'


    @api.model
    def payment_done(self, message):
        """缴费完成"""
        order_obj = self.env['sale.order']
        refund_apply_obj = self.env['his.refund_apply'].sudo()  # 退款申请

        data = json.loads(message.payload)

        orders = []
        for info in data['order_info']:
            order = order_obj.browse(info['id'])
            order.write({
                'internal_id': info['internal_id'], # 订单内部ID
                'commit_his_state': data['commit_his_state'], # 提交HIS状态
            })
            orders.append(order)

        # 修改支付结果信息
        if orders[0].pay_method == 'weixin':
            orders[0].weixin_pay_ids[0].internal_id = data['pay_record_internal_id'] # 支付记录内部ID

        if orders[0].pay_method == 'alipay':
            orders[0].alipay_ids[0].internal_id = data['pay_record_internal_id'] # 支付记录内部ID

        # 提交HIS失败
        if data['commit_his_state'] == '0':
            # 修改订单信息
            for order in orders:
                order.commit_his_error_msg = data['commit_his_error_msg']
            # 创建退款申请
            order = orders[0]
            res = {
                'partner_id': order.partner_id.id,
                'visit_partner_id': order.visit_partner_id.id,
                'pay_method': order.pay_method,
                'amount_total': sum([o.amount_total for o in orders]),
                'order_ids': [(6, 0, [o.id for o in orders])],
                'state': 'draft',
                'company_id': order.company_id.id,
                'internal_id': data['refund_apply_internal_id'],
                'reason': '缴费提交his发生错误',
            }
            if order.pay_method == 'weixin':
                res.update({
                    'weixin_pay_ids': [(6, 0, [weixin_pay.id for weixin_pay in order.weixin_pay_ids])]
                })
            if order.pay_method == 'alipay':
                res.update({
                    'alipay_ids': [(6, 0, [alipay.id for alipay in order.alipay_ids])]
                })

            refund_apply_obj.create(res)

    @api.model
    def recharge_done(self, message):
        """充值完成"""
        order_obj = self.env['sale.order']
        refund_apply_obj = self.env['his.refund_apply'].sudo()  # 退款申请

        data = json.loads(message.payload)

        order = order_obj.browse(data['order_id'])
        order.write({
            'internal_id': data['order_internal_id'],  # 订单内部ID
            'commit_his_state': data['commit_his_state'],  # 提交HIS状态
            'mz_balance': data.get('mz_balance', 0), # 门诊帐户余额
            'zy_balance': data.get('zy_balance', 0),  # 住院帐户余额
        })

        # 修改支付结果信息
        if order.pay_method == 'weixin':
            order.weixin_pay_ids[0].internal_id = data['pay_record_internal_id'] # 支付记录内部ID

        if order.pay_method == 'alipay':
            order.alipay_ids[0].internal_id = data['pay_record_internal_id'] # 支付记录内部ID

        # 提交HIS失败
        if data['commit_his_state'] == '0':
            # 修改订单信息
            order.commit_his_error_msg = data['commit_his_error_msg']

            # 创建退款申请
            res = {
                'partner_id': order.partner_id.id,
                'visit_partner_id': order.visit_partner_id.id,
                'pay_method': order.pay_method,
                'amount_total': order.amount_total,
                'order_ids': [(6, 0, [order.id])],
                'state': 'draft',
                'company_id': order.company_id.id,
                'internal_id': data['refund_apply_internal_id'],
                'reason': '充值提交his发生错误',
            }
            if order.pay_method == 'weixin':
                res.update({
                    'weixin_pay_ids': [(6, 0, [order.weixin_pay_ids[0].id])]
                })
            if order.pay_method == 'alipay':
                res.update({
                    'alipay_ids': [(6, 0, [order.alipay_ids[0].id])]
                })
            refund_apply_obj.create(res)

    @api.model
    def inoculation_appointment(self, message):
        """预防接种预约
            APP根据新生儿接种医院发送MQTT消息直接向内网ODOO预约,且等待直到接收到相同动作的MQTT消息，后进行支付处理或展示预约成功页面。
            内网收到消息处理完成后，向外网推送预约信息，同时返回相同动作的MQTT消息到APP
            外网收到内网的MQTT消息后，记录到数据库中
        """
        register_source_obj = self.env['his.register_source']
        company_obj = self.env['res.company']
        patient_obj = self.env['hrp.patient']

        data = json.loads(message.payload)
        source_id = data['source_id'] # 号源ID
        partner_id = data['partner_id'] # 新生儿内部ID
        reserve_record_id = data['reserve_record_id']  # 预约记录内部ID

        company = company_obj.search([('topic', '=', message.source_topic)]) # 医院
        register_source = register_source_obj.search([('company_id', '=', company.id), ('internal_id', '=', source_id)]) # 号源
        partner = patient_obj.search([('company_id', '=', company.id), ('internal_id', '=', partner_id)]).partner_id # 患者
        # 创建预约记录
        # self.env['hrp.appointment_record'].create({
        #     'partner_id': partner.id, # 患者
        #     'department_id': register_source.department_id.id, # 科室
        #     'company_id': company.id, # 医院
        #     'employee_id': False, # 医生
        #     'shift_type_id': register_source.shift_type_id.id, # 班次
        #     'register_source_id': register_source.id, # 号源
        #     'date': register_source.date, # 预约日期
        #     'order_id': False, # 关联订单
        #     'type': 'inoculation', # 类别
        #     'internal_id': reserve_record_id, # 内部ID
        #     'num': data['reserve_sort'], # 预约顺序号
        # })
        self.env['his.reserve_record'].sudo().create({
            'partner_id': partner.id,
            'reserve_date': register_source.date,
            'department_id': register_source.department_id.id,
            'employee_id': False,
            'shift_type_id': register_source.shift_type_id.id,
            'register_source_id': register_source.id,
            'reserve_sort': data['reserve_sort'],
            'order_id': False,
            'register_id': False,
            'type': 'inoculation',
            'state': 'draft',
            'company_id': register_source.company_id.id,
            'internal_id': False,
        })

    @api.model
    def inoculation_payed(self, message):
        """预防接种支付成功，通知内网, 内网返回"""
        order_obj = self.env['sale.order']

        data = json.loads(message.payload)
        weixin_internal_id = data['weixin_internal_id'] # 微信支付内部ID
        alipay_internal_id = data['alipay_internal_id'] # 支付宝支付内部ID
        order_internal_id = data['order_internal_id'] # 订单内部ID
        order_id = data['order_id']  # 订单ID

        order = order_obj.browse(order_id)

        order.internal_id = order_internal_id

        if order.pay_method == 'weixin':
            order.weixin_pay_record_ids[0].internal_id = weixin_internal_id

        if order.pay_method == 'alipay':
            order.alipay_record_ids[0].internal_id = alipay_internal_id

    @api.model
    def cancel_reserve_record(self, message):
        """取消预约挂号"""
        refund_apply_obj = self.env['his.refund_apply']  # 退款申请

        data = json.loads(message.payload)
        if data['refund_apply_id']:
            refund_apply_obj.browse(data['refund_apply_id']).internal_id = data['refund_apply_internal_id']

    @api.model
    def commit_reserve_record(self, message):
        """预约记录提交HIS后MQTT接口"""
        reserve_record_obj = self.env['his.reserve_record']  # 预约记录
        company_obj = self.env['res.company']

        for data in json.loads(message.payload):
            reserve_id = data['reserve_id'] # 预约记录内部ID
            commit_his_state = data['commit_his_state'] # 提交HIS状态

            company_id = company_obj.search([('topic', '=', message.source_topic)]).id

            reserve_record = reserve_record_obj.search([('company_id', '=', company_id), ('internal_id', '=', reserve_id)])
            if not reserve_record:
                continue

            res = {
                'commit_his_state': commit_his_state
            }
            if commit_his_state == '1':
                res.update({
                    'state': 'commit'
                })

            reserve_record.write(res)

            res = {
                'commit_his_state': commit_his_state
            }
            if commit_his_state == '0':
                res.update({
                    'commit_his_error_msg': data['commit_his_error_msg']
                })

            reserve_record.order_id.write(res)

    @api.model
    def schedule_shift_stop(self, message):
        """医院排班班次停诊"""
        def build_sms_signup_data():
            """构建注册验证短信请求参数"""

            parameters = {
                'userid': config['sms_userid'], # 企业id 1113
                'account': config['sms_account'], # 发送用户帐号 shango
                'password': config['sms_password'], # 发送帐号密码 123456
                'mobile': order.partner_id.phone, # 全部被叫号码
                'content': sms_content.encode('utf8'), # 发送内容
                'sendTime': '', # 定时发送时间
                'action': 'send',  # 发送任务命令
                'extno': '' # 扩展子号
            }
            parameters = urllib.urlencode(parameters)
            return parameters

        reserve_record_obj = self.env['his.reserve_record']  # 预约记录
        refund_apply_obj = self.env['his.refund_apply']  # 退款申请

        company_id = self.env['res.company'].search([('topic', '=', message.source_topic)]).id

        for data in json.loads(message.payload):
            refund_apply_internal_id = data['refund_apply_internal_id'] # 退款申请内部ID
            reserve_record_id = data['reserve_record_id'] # 预约记录内部ID

            reserve_record = reserve_record_obj.search([('company_id', '=', company_id), ('internal_id', '=', reserve_record_id)])

            # 取消订单
            order = reserve_record.order_id
            order.action_cancel()

            # 更新预约记录
            reserve_record.write({
                'state': 'cancel',
                'cancel_type': '2',  # 停诊取消
            })
            if order.pay_method not in ['free', 'coupon']:
                # 创建退款申请
                res = {
                    'partner_id': order.partner_id.id,
                    'visit_partner_id': reserve_record.partner_id.id,
                    'pay_method': order.pay_method,
                    'amount_total': order.amount_total,
                    'order_ids': [(6, 0, [order.id])],
                    'state': 'draft',
                    'company_id': company_id,
                    'reason': '停诊,取消预约挂号',
                    'internal_id': refund_apply_internal_id, # 退款申请内部ID
                }
                if order.pay_method == 'weixin':
                    res.update({
                        'weixin_pay_ids': [(6, 0, [weixin_pay.id for weixin_pay in order.weixin_pay_ids])]
                    })
                if order.pay_method == 'alipay':
                    res.update({
                        'alipay_ids': [(6, 0, [alipay.id for alipay in order.alipay_ids])]
                    })
                refund_apply_obj.create(res)

            # 发送短信息
            sms_content = u'【GLEKE】%s%s%s医生%s%s停诊，您预约的%s的号被取消。' % (
                reserve_record.company_id.name,
                reserve_record.department_id.name,
                reserve_record.employee_id.name,
                reserve_record.reserve_date,
                reserve_record.shift_type_id.name,
                reserve_record.register_source_id.time_point_name)  # 短信内容

            if order.pay_method not in ['free', 'coupon']:
                sms_content += u'已支付的金额:%s元将在24小时内退回到你的%s账户中' % (order.amount_total, {'weixin': u'微信', 'alipay': u'支付宝', 'long': u'龙支付'}[order.pay_method]) # 短信内容

            # 发送短信数据
            sms_data = build_sms_signup_data()

            # SMS短信请求
            try:
                sms_request = urllib2.Request(config['sms_gateway'], sms_data)
                urllib2.urlopen(sms_request)
            except Exception, e:
                _logger.error('停诊发送短信失败')
                _logger.error(traceback.format_exc())
                _logger.error(e.message)

    @api.model
    def service_pay_done(self, message):
        """划价完成"""
        order_obj = self.env['sale.order']
        refund_apply_obj = self.env['his.refund_apply'].sudo()  # 退款申请

        data = json.loads(message.payload)

        order = order_obj.browse(data['order_id'])
        order.write({
            'internal_id': data['order_internal_id'],  # 订单内部ID
            'commit_his_state': data['commit_his_state'],  # 提交HIS状态
        })

        # 修改支付结果信息
        if order.pay_method == 'weixin':
            order.weixin_pay_ids[0].internal_id = data['pay_record_internal_id'] # 支付记录内部ID

        if order.pay_method == 'alipay':
            order.alipay_ids[0].internal_id = data['pay_record_internal_id'] # 支付记录内部ID

        # 提交HIS失败
        if data['commit_his_state'] == '0':
            # 修改订单信息
            order.commit_his_error_msg = data['commit_his_error_msg']

            # 创建退款申请
            res = {
                'partner_id': order.partner_id.id,
                'visit_partner_id': order.visit_partner_id.id,
                'pay_method': order.pay_method,
                'amount_total': order.amount_total,
                'order_ids': [(6, 0, [order.id])],
                'state': 'draft',
                'company_id': order.company_id.id,
                'internal_id': data['refund_apply_internal_id'],
                'reason': '划价收费提交his发生错误',
            }
            if order.pay_method == 'weixin':
                res.update({
                    'weixin_pay_ids': [(6, 0, [order.weixin_pay_ids[0].id])]
                })
            if order.pay_method == 'alipay':
                res.update({
                    'alipay_ids': [(6, 0, [order.alipay_ids[0].id])]
                })
            refund_apply_obj.create(res)











