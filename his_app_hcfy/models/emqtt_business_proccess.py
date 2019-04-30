# -*- encoding:utf-8 -*-
import json
from datetime import datetime, timedelta
import logging

from dateutil.relativedelta import relativedelta
from odoo.addons.his_data_synchronization_poll.ora import Ora
from odoo import api
from odoo import models
from odoo.tools import config, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

_logger = logging.getLogger(__name__)


class EmqttBusinessProcess(models.TransientModel):
    """Emqtt业务处理"""
    _inherit = 'his.emqtt'


    @api.model
    def app_start(self, message):
        """APP运行，广播，保存APP的令牌和MAC"""
        data = json.loads(message.payload)
        self.env['his.app_token'].sudo().create({
            'mac': data['mac'],
            'token': data['token'],
        })

    @api.model
    def add_patient(self, message):
        """添加就诊人"""
        def get_update_value():
            values = {'card_type_id': card_type_id}

            if partner.extranet_id != extranet_id:
                values['extranet_id'] = extranet_id

            if partner.name != name:
                values['name'] = name

            if partner.phone != phone:
                values['phone'] = phone

            if partner.birth_date != birth_date:
                values['birth_date'] = birth_date

            if partner.patient_property != patient_property:
                values['patient_property'] = patient_property

            if partner.work_company != work_company:
                values['work_company'] = work_company

            if partner.address != address:
                values['address'] = address

            if partner.inoculation_code != inoculation_code:
                values['inoculation_code'] = inoculation_code

            if partner.note_code != note_code:
                values['note_code'] = note_code

            if partner.last_menstruation_day != last_menstruation_day:
                values['last_menstruation_day'] = last_menstruation_day

            if partner.plan_born_day != plan_born_day:
                values['plan_born_day'] = plan_born_day

            return values

        def compute_age():
            today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)  # 当前日期
            birthday = datetime.strptime(birth_date, DATE_FORMAT)  # 出生日期
            ages = relativedelta(today, birthday)  # 新生儿年龄

            months = ages.years * 12 + ages.months  # 出生到现在月数
            if not months:
                return u'%d天' % ages.days
            elif not ages.years:
                return u'%d个月+%d天' % (ages.months, ages.days) if ages.days else u'%d个月' % ages.months
            else:
                return u'%d' % ages.years

        def create_partner(card_type_id1):
            """创建患者"""
            return partner_obj.create({
                'extranet_id': extranet_id,  # 处网ID
                'patient_property': patient_property,  # 患者性质
                'name': name,  # 姓名
                'gender': gender,  # 性别
                'sex': '男' if gender == 'male' else '女', # 性别
                'id_no': identity_no,  # 身份证号
                'medical_no': medical_no,  # 医保卡号
                'phone': phone,  # 电话
                'work_company': work_company,  # 工作单位
                'address': address,  # 家庭住址
                'birth_date': birth_date,  # 新生儿出生日期
                'inoculation_code': inoculation_code,  # 儿童编码
                'note_code': note_code,  # 接种本条形码
                'last_menstruation_day': last_menstruation_day,  # 孕妇末次月经日期
                'plan_born_day': plan_born_day,  # 孕妇预产期
                'customer': True,  # 是客户
                'is_patient': True,  # 是患者

                'card_no': partner_info['card_no'], # 就诊卡号
                'outpatient_num': partner_info['outpatient_num'], # 门诊号
                'hospitalize_no': partner_info['hospitalize_no'], # 住院号
                'his_id': partner_info['his_id'], # HIS_ID
                # 'card_type_id': config['treatment_card_type_id'], # 识别患者的卡类型ID: 就诊卡
                'card_type_id': card_type_id1,
            })

        partner_obj = self.env['res.partner']
        interface_obj = self.env['his.interface']

        data = json.loads(message.payload)

        extranet_id = data['partner_id'] # 外部ID
        identity_no = data['identity_no'] # 身份证号
        medical_no = data['medical_card'] # 医保卡号
        name = data['name'] # 姓名
        gender = data['gender'] # 性别
        phone = data['phone'] # 电话
        birth_date = data['birth_date'] # 出生日期
        patient_property = data['patient_property'] # 患者性质
        work_company = data['company_name'] # 工作单位
        address = data['address'] # 家庭住址
        inoculation_code = data['inoculation_code'] # 儿童编码
        note_code = data['note_code'] # 接种本条形码
        last_menstruation_day = data['last_menstruation_day'] # 孕妇末次月经日期
        plan_born_day = data['plan_born_day'] # 孕妇预产期


        his_exist = False # 病人是否在HIS中存在
        card_type_id = False # 卡类别ID
        card_no = False # 就诊卡号
        if identity_no:
            res = interface_obj.id_no_exist(identity_no) # 身份证是否在HIS中办过就诊卡
            if res['state']:
                his_exist = 1
                card_type_id = config['identity_card_type_id'] # 身份识别时卡类别id:二代身份证
                card_no = identity_no
        elif medical_no:
            res = interface_obj.medical_no_exist(medical_no)# 医保卡号是否办过就诊卡
            if res['state']:
                his_exist = 1
                card_type_id = config['medical_card_type_id'] # 身份识别时卡类别id:重庆市医保卡
                card_no = medical_no

        if his_exist == 1:
            # 从HIS中获取病人信息(his_id)
            partner_info = interface_obj.get_patient_info(card_no, card_type_id) # HIS返回的患者信息 门诊号，住院号，就诊卡号，his_id
            if partner_info['card_no']:
                card_type_id = config['treatment_card_type_id']  # 就诊卡
                card_no = partner_info['card_no']
            elif partner_info['outpatient_num']:
                card_no = partner_info['outpatient_num']
            else:
                card_no = ''

            his_id = partner_info['his_id']
            partner = partner_obj.search([('his_id', '=', his_id)])
            if partner:
                vals = get_update_value()
                vals['card_type_id'] = card_type_id
                partner.write(vals)

                # TODO
                # 创建接种记划
                # 创建孕检记划
                # 创建儿保计划
            else:
                partner = create_partner(card_type_id)

        else:
            # HIS建档
            sex = u'男' if gender == 'male' else u'女'
            card_no = self.env['ir.sequence'].next_by_code('partner.card_no') # 就诊卡号
            card_type_id = config['treatment_card_type_id'] # 身份识别时卡类别id: 就诊卡
            age = compute_age()
            his_id = interface_obj.add_patient(name, sex, identity_no, phone, birth_date, card_no, card_type_id, age)['his_id']
            partner = partner_obj.search([('his_id', '=', his_id)])
            if partner:
                vals = get_update_value()
                vals['card_type_id'] = card_type_id

                partner.write(vals)

                # TODO
                # 创建接种记划
                # 创建孕检记划
                # 创建儿保计划
            else:
                partner_info = {
                    'card_no': card_no,
                    'outpatient_num': '',
                    'hospitalize_no': '',
                    'his_id': his_id
                }
                partner = create_partner(card_type_id)

        # 返回添加就诊人
        return message.source_topic, {
            'action': 'add_patient',
            'data': {
                'partner_id': data['partner_id'], # 患者ID
                'internal_id': partner.id, # 患者内部ID
                'card_no': card_no, # 就诊卡号
            }
        }

    @api.model
    def lock_register_source(self, message):
        """APP预约挂号支付前锁定号源MQTT接口"""
        data = json.loads(message.payload)
        result = self.env['his.register_source'].lock_register_source(data['internal_id'])
        _logger.info(result)

        return message.source_topic, {
            'action': 'lock_register_source',
            'data': result
        }

    @api.model
    def unlock_register_source(self, message):
        """APP预约挂号离开支付页面或超时解锁号源MQTT接口"""
        data = json.loads(message.payload)
        result = self.env['his.register_source'].unlock_register_source(data['internal_id'])
        return message.source_topic, {
            'action': 'unlock_register_source',
            'data': result
        }

    @api.model
    def register_done(self, message):
        """挂号完成，外网处理完成后向内网发送MQTT接口"""
        def create_order():
            """创建订单"""
            department_employee = department_employee_obj.search([('department_id', '=', department_id), ('employee_id', '=', employee_id)])  # 科室排班人员
            order_res = order_obj.create({
                'partner_id': partner.id,
                'pay_method': pay_method,
                'order_type': 'register',
                'state': 'sale',
            })

            if pay_method not in ['free', 'coupon']:
                for product in department_employee.product_ids:
                    order_line_obj.create({
                        'order_id': order_res.id,
                        'product_id': product.product_variant_id.id,
                        'name': product.name,
                        'product_uom_qty': 1,
                        'product_uom': product.uom_id.id,
                        'price_unit': product.list_price
                    })

            return order_res

        def create_weixin_pay_record():
            """创建微信支付记录"""
            return weixin_pay_record_obj.create({
                'return_code': pay_result.get('return_code'), # 返回状态码
                'return_msg': pay_result.get('return_msg'), # 返回信息
                'appid': pay_result.get('appid'), # 应用ID
                'mch_id': pay_result.get('mch_id'), # 商户号
                'device_info': pay_result.get('device_info'), # 设备号
                'nonce_str': pay_result.get('nonce_str'), # 随机字符串
                'sign': pay_result.get('sign'), # 签名
                'result_code': pay_result.get('result_code'), # 业务结果
                'err_code': pay_result.get('err_code'), # 错误代码
                'err_code_des': pay_result.get('err_code_des'), # 错误代码描述
                'openid': pay_result.get('openid'), # 用户标识
                'is_subscribe': pay_result.get('is_subscribe'), # 是否关注公众账号
                'trade_type': pay_result.get('trade_type'), # 交易类型
                'bank_type': pay_result.get('bank_type'), # 付款银行
                'total_fee': pay_result.get('total_fee'), # 总金额
                'fee_type': pay_result.get('fee_type'), # 货币种类
                'cash_fee': pay_result.get('cash_fee'), # 现金支付金额
                'cash_fee_type': pay_result.get('cash_fee_type'), # 现金支付货币类型
                'transaction_id': pay_result.get('transaction_id'), # 微信支付订单号
                'out_trade_no': pay_result.get('out_trade_no'), # 商户订单号
                'attach': pay_result.get('attach'), # 商家数据包
                'time_end': pay_result.get('time_end'), # 支付完成时间
                'order_ids': [(6, 0, [order.id])],
            })

        def create_alipay_record():
            """创建支付宝支付记录"""
            return alipay_record_obj.create({
                'notify_time': pay_result['notify_time'], # 通知时间')
                'notify_type': pay_result['notify_type'], # 通知类型')
                'notify_id': pay_result['notify_id'], # 通知校验ID')
                'app_id': pay_result['app_id'], # 应用Id')
                'charset': pay_result['charset'], # 编码格式')
                'version': pay_result['version'], # 接口版本')
                'sign_type': pay_result['sign_type'], # 签名类型')
                'sign': pay_result['sign'], # 签名')
                'trade_no': pay_result['trade_no'], # 支付宝交易号')
                'out_trade_no': pay_result['out_trade_no'], # 商户订单号')
                'trade_status': pay_result['trade_status'], # 交易状态')
                'total_amount': pay_result['total_amount'], # 订单金额')
                'receipt_amount': pay_result['receipt_amount'], # 实收金额')
                'buyer_pay_amount': pay_result['buyer_pay_amount'], # 付款金额')
                'gmt_create': pay_result['gmt_create'], # 交易创建时间')
                'gmt_payment': pay_result['gmt_payment'], # 交易付款时间')
                'gmt_close': pay_result.get('gmt_close'), # 交易结束时间')
                'passback_params': pay_result['passback_params'], # 回传参数')

                'order_ids': [(6, 0, [order.id])],
            })

        def create_reserve_record():
            """创建预约记录"""
            return reserve_record_obj.create({
                'partner_id': partner.id,  # 患者
                'reserve_date': appointment_record_info['date'],  # 预约日期
                'department_id': appointment_record_info['department_id'],  # 科室
                'employee_id': appointment_record_info['employee_id'],  # 医生
                'shift_type_id': appointment_record_info['shift_id'],  # 班次
                'register_source_id': register_source_id,  # 号源
                'type': 'register', # 预约类别s
                'order_id': order.id,  # 订单
                'state': 'reserve',  # 状态
            })

        def create_treatment_process():
            """就医流程"""
            visit_date = appointment_record_info['date'] # 就诊日期
            # 手动完成以前还没有完成的就医流程
            treatment_process_obj.search([('visit_date', '<', today), ('partner_id', '=', partner.id), ('state', '=', 'doing')]).write({
                'state': 'done'
            })
            treatment_process = treatment_process_obj.search([('visit_date', '=', visit_date), ('partner_id', '=', partner.id), ('state', '=', 'doing')])
            if not treatment_process:
                treatment_process = treatment_process_obj.create({
                    'partner_id': partner.id,
                    'visit_date': visit_date,
                    'state': 'doing'
                })


            treatment_process_line_obj.create({
                'process_id': treatment_process.id,
                'code': '01',
                'name': '挂号', # 流程名称
                'business': '挂号', # 业务类型
                'department_id': department_id,
                'employee_id': employee_id,
                'location': department_obj.browse(department_id).location or '',
                'update_time': datetime.now().strftime(DATETIME_FORMAT),
                'process_type': '2', # 流程类型 '1', '排队'  '2', '不排队'
                'state': 'done',
                'reserve_id': reserve_record.id,

                'message': '|'.join([appointment_record_info['date'], register_source.time_point_name, reserve_sort, reserve_record.employee_id.name]), # 就诊日期|时间点|预约号|医生名称
            })

        def create_long_pay_record():
            return long_pay_record_obj.create({
                'POSID': pay_result.get('POSID'),
                'BRANCHID': pay_result.get('BRANCHID'),
                'ORDERID': pay_result.get('ORDERID'),
                'PAYMENT': pay_result.get('PAYMENT'),
                'CURCODE': pay_result.get('CURCODE'),
                'REMARK1': pay_result.get('REMARK1'),
                'REMARK2': pay_result.get('REMARK2'),
                'ACC_TYPE': pay_result.get('ACC_TYPE'),
                'SUCCESS': pay_result.get('SUCCESS'),
                'TYPE': pay_result.get('TYPE'),
                'REFERER': pay_result.get('REFERER'),
                'CLIENTIP': pay_result.get('CLIENTIP'),
                'ACCDATE': pay_result.get('ACCDATE'),
                'USRMSG': pay_result.get('USRMSG'),
                'INSTALLNUM': pay_result.get('INSTALLNUM'),
                'ERRMSG': pay_result.get('ERRMSG'),
                'USRINFO': pay_result.get('USRINFO'),
                'DISCOUNT': pay_result.get('DISCOUNT'),
                'SIGN': pay_result.get('SIGN'),

                'order_ids': [(6, 0, [order.id])],
            })


        partner_obj = self.env['res.partner']  # 合作伙伴
        order_obj = self.env['sale.order']  # 订单
        order_line_obj = self.env['sale.order.line']  # 订单明细
        weixin_pay_record_obj = self.env['his.weixin_pay_record']  # 微信支付记录
        alipay_record_obj = self.env['his.alipay_record']  # 支付宝支付记录
        reserve_record_obj = self.env['his.reserve_record']  # 预约记录
        department_employee_obj = self.env['his.schedule_department_employee']  # 科室排班人员
        department_obj = self.env['hr.department'] # 科室
        register_source_obj = self.env['his.register_source']  # 号源
        register_plan_obj = self.env['his.register_plan']  # 挂号记划表
        treatment_process_obj = self.env['hrp.treatment_process'] # 就医流程主记录
        treatment_process_line_obj = self.env['hrp.treatment_process_line'] # 就医流程明细记录
        refund_apply_obj = self.env['his.refund_apply'].sudo()  # 退款申请
        long_pay_record_obj = self.env['his.long_pay_record'].sudo()  # 龙支付记录


        data = json.loads(message.payload)

        appointment_record_info = data['appointment_record']  # 预约记录信息
        department_id = appointment_record_info['department_id']
        employee_id = appointment_record_info['employee_id']
        register_source_id = appointment_record_info['register_source_id']  # 号源ID
        pay_method = data['pay_method']  # 支付方式
        pay_result = data['pay_result']  # 支付结果
        register_source = register_source_obj.browse(register_source_id)  # 号源
        today = datetime.now().strftime(DATE_FORMAT)

        partner = partner_obj.browse(data['partner_id'])

        department_employee = department_employee_obj.search([('department_id', '=', department_id), ('employee_id', '=', employee_id)])  # 科室排班人员

        # 创建订单
        order = create_order()

        # 创建支付记录
        pay_record = None
        # if pay_method != u'free':
        if pay_method not in ['free', 'coupon']:
            pay_record = None  # 支付记录
            if pay_method == 'weixin':
                pay_record = create_weixin_pay_record()
            if pay_method == 'alipay':
                pay_record = create_alipay_record()
            if pay_method == 'longpay':
                pay_record = create_long_pay_record()

        # 创建预约记录
        reserve_record = create_reserve_record()

        # 修改号源状态
        has_error = False # 号源被系统自动解锁，发生错误
        try:
            register_source_obj.appointment_register(register_source_id)  # 号源状态改为已经预约
        except Exception, e:
            _logger.error(u'挂号完成，号源被系统自动解锁，发生错误')
            _logger.error(e.message)
            has_error = True

        # 发送到外网的数据
        result = {
            'appointment_record': {
                'id': appointment_record_info['id'],  # 预约记录的外网ID
                'internal_id': reserve_record.id,  # 预约记录的内部ID
                'reserve_sort': reserve_record.reserve_sort or '',  # 预约顺序号
            },
            'pay_record_internal_id': pay_record.id if pay_result else None,
            'order_internal_id': order.id
        }

        if not has_error:
            reserve_sort = ''
            # 修改号源安排表
            register_plan = register_plan_obj.search([('medical_date', '=', appointment_record_info['date']), ('department_id', '=', department_id), ('employee_id', '=', employee_id)])
            for line in register_plan.line_ids:
                if line.time_point_name == register_source.time_point_name:
                    line.write({
                        'partner_id': partner.id,
                        'source': 'app',
                        'register_time': datetime.now().strftime(DATETIME_FORMAT),
                        'reserve_time_point_name': register_source.time_point_name
                    })
                    reserve_sort = '%s%03d' % (department_employee.queue_prefix or 'A', line.medical_sort)
                    reserve_record.reserve_sort = reserve_sort  # 预约顺序号
                    break

            # 创建就医流程
            create_treatment_process()

            # 修改返回到外网的数据
            result['appointment_record']['reserve_sort'] = reserve_record.reserve_sort
        else:
            # 创建退款申请
            # if pay_method != u'free':
            if pay_method not in ['free', 'coupon']:
                res = {
                    'visit_partner_id': reserve_record.partner_id.id,
                    'pay_method': order.pay_method,
                    'amount_total': order.amount_total,
                    'order_ids': [(6, 0, [order.id])],
                    'state': 'draft',
                    'order_type': order.order_type,
                    'reason': '创建挂号发生错误，号源被占用'
                }
                if order.pay_method == 'weixin':
                    res.update({
                        'weixin_pay_ids': [(6, 0, [pay_record.id])],
                        'transaction_id': pay_record.transaction_id
                    })
                if order.pay_method == 'alipay':
                    res.update({
                        'alipay_ids': [(6, 0, [pay_record.id])],
                        'trade_no': pay_record.trade_no
                    })
                if order.pay_method == 'longpay':
                    res.update({
                        'long_pay_record_ids': [(6, 0, [pay_record.id])],
                        'trade_no': pay_record.ORDERID
                    })
                refund_apply = refund_apply_obj.create(res)
                # 修改通知消息
                message.refund_apply_id = refund_apply.id
                result.update({
                    'refund_apply_internal_id': refund_apply.id,  # 退款申请内部ID
                })

            # 修改预约记录状态
            reserve_record.state = 'draft'


        return message.source_topic, {
            'action': 'register_done',
            'data': result
        }

    @api.model
    def get_treatment_process(self, message):
        """得到就医流程"""
        treatment_process_obj = self.env['hrp.treatment_process'] # 就医流程主记录

        data = json.loads(message.payload)
        data.update({
            'topic': message.source_topic
        })
        result = treatment_process_obj.get_process(data)

        return message.source_topic, {
            'action': 'get_treatment_process',
            'data': result
        }

    @api.model
    def get_payment_list(self, message):
        """得到门诊缴费清单"""
        data = json.loads(message.payload)
        try:
            pay_list = self.env['his.interface'].get_payment_list(data['partner_id'])
            result = {'data': {'state': 1, 'result': pay_list}}
        except Exception, e:
            result = {'data': {'state': 0, 'msg': e.message}}

        return message.source_topic, {
            'action': 'get_payment_list',
            'data': result
        }

    @api.model
    def payment_done(self, message):
        """缴费完成, 外网处理完成后向内网发送MQTT接口"""
        def create_order():
            """创建订单"""
            for info in order_detail:
                order_line = []
                for detail in info['details']:
                    product = product_obj.browse(detail['product_id'])
                    order_line.append((0, 0, {
                        'product_id': detail['product_id'],
                        'name': detail['name'],
                        'product_uom_qty': detail['qty'],
                        'price_unit': detail['price'],
                        'product_uom': product.uom_id.id,
                        'fee_name': detail['fee_name'],  # 收据费目
                        'tax_id': False,
                    }))
                o = order_obj.create({
                    'partner_id': partner_id, # 患者ID,
                    'pay_method': pay_method, # 支付方式,
                    'order_type': 'payment',
                    'receipt_no': info['receipt_no'], # 单据号
                    'order_line': order_line,
                    'state': 'sale',
                })
                orders.append(o)
                order_info.append({
                    'id': info['id'], # 订单外网id
                    'internal_id': o.id # 订单内部ID
                })

        def create_weixin_pay_record():
            """创建微信支付记录"""
            return weixin_pay_record_obj.create({
                'return_code': pay_result.get('return_code'), # 返回状态码
                'return_msg': pay_result.get('return_msg'), # 返回信息
                'appid': pay_result.get('appid'), # 应用ID
                'mch_id': pay_result.get('mch_id'), # 商户号
                'device_info': pay_result.get('device_info'), # 设备号
                'nonce_str': pay_result.get('nonce_str'), # 随机字符串
                'sign': pay_result.get('sign'), # 签名
                'result_code': pay_result.get('result_code'), # 业务结果
                'err_code': pay_result.get('err_code'), # 错误代码
                'err_code_des': pay_result.get('err_code_des'), # 错误代码描述
                'openid': pay_result.get('openid'), # 用户标识
                'is_subscribe': pay_result.get('is_subscribe'), # 是否关注公众账号
                'trade_type': pay_result.get('trade_type'), # 交易类型
                'bank_type': pay_result.get('bank_type'), # 付款银行
                'total_fee': pay_result.get('total_fee'), # 总金额
                'fee_type': pay_result.get('fee_type'), # 货币种类
                'cash_fee': pay_result.get('cash_fee'), # 现金支付金额
                'cash_fee_type': pay_result.get('cash_fee_type'), # 现金支付货币类型
                'transaction_id': pay_result.get('transaction_id'), # 微信支付订单号
                'out_trade_no': pay_result.get('out_trade_no'), # 商户订单号
                'attach': pay_result.get('attach'), # 商家数据包
                'time_end': pay_result.get('time_end'), # 支付完成时间
                'order_ids': [(6, 0, [order.id for order in orders])],
            })

        def create_alipay_record():
            """创建支付宝支付记录"""
            return alipay_record_obj.create({
                'notify_time': pay_result['notify_time'], # 通知时间')
                'notify_type': pay_result['notify_type'], # 通知类型')
                'notify_id': pay_result['notify_id'], # 通知校验ID')
                'app_id': pay_result['app_id'], # 应用Id')
                'charset': pay_result['charset'], # 编码格式')
                'version': pay_result['version'], # 接口版本')
                'sign_type': pay_result['sign_type'], # 签名类型')
                'sign': pay_result['sign'], # 签名')
                'trade_no': pay_result['trade_no'], # 支付宝交易号')
                'out_trade_no': pay_result['out_trade_no'], # 商户订单号')
                'trade_status': pay_result['trade_status'], # 交易状态')
                'total_amount': pay_result['total_amount'], # 订单金额')
                'receipt_amount': pay_result['receipt_amount'], # 实收金额')
                'buyer_pay_amount': pay_result['buyer_pay_amount'], # 付款金额')
                'gmt_create': pay_result['gmt_create'], # 交易创建时间')
                'gmt_payment': pay_result['gmt_payment'], # 交易付款时间')
                'gmt_close': pay_result.get('gmt_close'), # 交易结束时间')
                'passback_params': pay_result['passback_params'], # 回传参数')

                'order_ids': [(6, 0, [order.id for order in orders])],
            })

        def create_long_pay_record():
            return long_pay_record_obj.create({
                'POSID': pay_result.get('POSID'),
                'BRANCHID': pay_result.get('BRANCHID'),
                'ORDERID': pay_result.get('ORDERID'),
                'PAYMENT': pay_result.get('PAYMENT'),
                'CURCODE': pay_result.get('CURCODE'),
                'REMARK1': pay_result.get('REMARK1'),
                'REMARK2': pay_result.get('REMARK2'),
                'ACC_TYPE': pay_result.get('ACC_TYPE'),
                'SUCCESS': pay_result.get('SUCCESS'),
                'TYPE': pay_result.get('TYPE'),
                'REFERER': pay_result.get('REFERER'),
                'CLIENTIP': pay_result.get('CLIENTIP'),
                'ACCDATE': pay_result.get('ACCDATE'),
                'USRMSG': pay_result.get('USRMSG'),
                'INSTALLNUM': pay_result.get('INSTALLNUM'),
                'ERRMSG': pay_result.get('ERRMSG'),
                'USRINFO': pay_result.get('USRINFO'),
                'DISCOUNT': pay_result.get('DISCOUNT'),
                'SIGN': pay_result.get('SIGN'),

                'order_ids': [(6, 0, [order.id])],
            })

        order_obj = self.env['sale.order']  # 订单
        weixin_pay_record_obj = self.env['his.weixin_pay_record']  # 微信支付记录
        alipay_record_obj = self.env['his.alipay_record']  # 支付宝支付记录
        product_obj = self.env['product.template'] # 产品
        refund_apply_obj = self.env['his.refund_apply'].sudo()  # 退款申请
        long_pay_record_obj = self.env['his.long_pay_record'].sudo()  # 龙支付记录

        data = json.loads(message.payload)
        pay_method = data['pay_method']  # 支付方式
        pay_result = data['pay_result']  # 支付结果
        order_detail = data['order_info']  # 订单信息
        partner_id = data['partner_id'] # 患者

        order_info = [] # 待返回的订单信息

        # 创建订单
        orders = []
        create_order()

        # 创建支付记录
        pay_record = None # 支付记录
        if pay_method == 'weixin':
            pay_record = create_weixin_pay_record()
        if pay_method == 'alipay':
            pay_record = create_alipay_record()
        if pay_method == 'longpay':
            pay_record = create_long_pay_record()

        result = {
            'order_info': order_info,
            'pay_record_internal_id': pay_record.id,  # 支付记录内部ID
            'commit_his_state': '1' # 提交HIS状态
        }

        # 提交HIS
        try:
            res = self.env['his.interface'].payment_commit_his(orders) # tran_flow医院结算流水号
            pay_record.tran_flow = res['tran_flow']
            for order in orders:
                order.write({
                    'commit_his_state': '1',
                    'tran_flow': res['tran_flow']
                })
        except Exception, e:
            _logger.error(u'缴费提交HIS错误')
            _logger.error(e.message)
            # 修改订单信息
            for order in orders:
                order.write({
                    'commit_his_state': '0',
                    'commit_his_error_msg': e.message
                })

            # 创建退款申请
            res = {
                'visit_partner_id': partner_id,
                'pay_method': orders[0].pay_method,
                'amount_total': sum([order.amount_total for order in orders]),
                'order_ids': [(6, 0, [order.id for order in orders])],
                'state': 'draft',
                'order_type': orders[0].order_type,
                'reason': '缴费提交his发生错误'
            }
            if orders[0].pay_method == 'weixin':
                res.update({
                    'weixin_pay_ids': [(6, 0, [pay_record.id])],
                    'transaction_id': pay_record.transaction_id
                })
            if orders[0].pay_method == 'alipay':
                res.update({
                    'alipay_ids': [(6, 0, [pay_record.id])],
                    'trade_no': pay_record.trade_no
                })
            if orders[0].pay_method == 'longpay':
                res.update({
                    'long_pay_record_ids': [(6, 0, [pay_record.id])],
                    'trade_no': pay_record.ORDERID
                })
            refund_apply = refund_apply_obj.create(res)
            # 修改通知消息
            message.refund_apply_id = refund_apply.id
            result.update({
                'refund_apply_internal_id': refund_apply.id, # 退款申请内部ID
                'commit_his_error_msg': e.message, # 提交HIS错误信息
                'commit_his_state': '0', # 提交HIS状态
            })

        return message.source_topic, {
            'action': 'payment_done',
            'data': result
        }

    @api.model
    def get_payment_record(self, message):
        """查询已缴费接口"""
        data = json.loads(message.payload)
        try:
            try:
                start_date = data.get('start_date')
                end_date = data.get('end_date')
                datetime.strptime(start_date, DATE_FORMAT)
                datetime.strptime(end_date, DATE_FORMAT)
            except:
                raise Exception(u'日期格式错误!')

            payment_record = self.env['his.interface'].get_payment_record(data['partner_id'], start_date, end_date)
            result = {'data': {'state': 1, 'result': payment_record}}
        except Exception, e:
            result = {'data': {'state': 0, 'msg': e.message}}

        return message.source_topic, {
            'action': 'get_payment_record',
            'data': result
        }

    @api.model
    def get_recharge_record(self, message):
        """查询充值记录"""
        data = json.loads(message.payload)
        try:
            try:
                start_date = data.get('start_date')
                end_date = data.get('end_date')
                datetime.strptime(start_date, DATE_FORMAT)
                datetime.strptime(end_date, DATE_FORMAT)
            except:
                raise Exception(u'日期格式错误!')

            recharge_record = self.env['his.interface'].get_recharge_record(data['partner_id'], start_date, end_date, data['recharge_type'])
            result = {'data': {'state': 1, 'result': recharge_record}}
        except Exception, e:
            result = {'data': {'state': 0, 'msg': e.message}}

        return message.source_topic, {
            'action': 'get_recharge_record',
            'data': result
        }

    @api.model
    def get_register_record(self, message):
        """查询挂号记录"""
        data = json.loads(message.payload)
        try:
            try:
                start_date = data.get('start_date')
                end_date = data.get('end_date')
                start_date = (datetime.strptime(start_date, DATE_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT)
                end_date = (datetime.strptime(end_date, DATE_FORMAT) - timedelta(hours=8)).strftime(DATETIME_FORMAT)
            except:
                raise Exception(u'日期格式错误!')

            register_record = self.env['his.register'].search([('partner_id', '=', data['partner_id']), ('create_date', '>=', start_date), ('create_date', '<=', end_date)])
            result = {
                'data': {
                    'state': 1,
                    'result': [{
                        'department': register.department_id.name,
                        'employee': register.employee_id.name if register.employee_id else '',
                        'register_type': register.register_type,
                        'register_datetime': register.register_datetime
                    }for register in register_record]
                }
            }
        except Exception, e:
            result = {'data': {'state': 0, 'msg': e.message}}

        return message.source_topic, {
            'action': 'get_payment_record',
            'data': result
        }

    @api.model
    def recharge_done(self, message):
        """充值完成, 外网处理完成后向内网发送MQTT接口"""

        def create_order():
            """创建订单"""
            product_category = product_category_obj.search([('name', '=', u'充值')])
            product = product_obj.search([('categ_id', '=', product_category.id)])

            order_line = [(0, 0, {
                'product_id': product.product_variant_id.id,
                'name': product.name,
                'product_uom_qty': 1,
                'price_unit': amount,
                'product_uom': product.uom_id.id,
                # 'fee_name': detail['fee_name'],  # 收据费目
                'tax_id': False,
            })]
            order = order_obj.create({
                'partner_id': partner_id,  # 患者ID,
                'pay_method': pay_method,  # 支付方式,
                'order_type': 'recharge',
                # 'receipt_no': info['receipt_no'],  # 单据号
                'order_line': order_line,
                'recharge_type': recharge_type,
                'state': 'sale',
            })

            return order

        def create_weixin_pay_record():
            """创建微信支付记录"""
            return weixin_pay_record_obj.create({
                'return_code': pay_result.get('return_code'), # 返回状态码
                'return_msg': pay_result.get('return_msg'), # 返回信息
                'appid': pay_result.get('appid'), # 应用ID
                'mch_id': pay_result.get('mch_id'), # 商户号
                'device_info': pay_result.get('device_info'), # 设备号
                'nonce_str': pay_result.get('nonce_str'), # 随机字符串
                'sign': pay_result.get('sign'), # 签名
                'result_code': pay_result.get('result_code'), # 业务结果
                'err_code': pay_result.get('err_code'), # 错误代码
                'err_code_des': pay_result.get('err_code_des'), # 错误代码描述
                'openid': pay_result.get('openid'), # 用户标识
                'is_subscribe': pay_result.get('is_subscribe'), # 是否关注公众账号
                'trade_type': pay_result.get('trade_type'), # 交易类型
                'bank_type': pay_result.get('bank_type'), # 付款银行
                'total_fee': pay_result.get('total_fee'), # 总金额
                'fee_type': pay_result.get('fee_type'), # 货币种类
                'cash_fee': pay_result.get('cash_fee'), # 现金支付金额
                'cash_fee_type': pay_result.get('cash_fee_type'), # 现金支付货币类型
                'transaction_id': pay_result.get('transaction_id'), # 微信支付订单号
                'out_trade_no': pay_result.get('out_trade_no'), # 商户订单号
                'attach': pay_result.get('attach'), # 商家数据包
                'time_end': pay_result.get('time_end'), # 支付完成时间
                'order_ids': [(6, 0, [order.id])],
            })

        def create_alipay_record():
            """创建支付宝支付记录"""
            return alipay_record_obj.create({
                'notify_time': pay_result['notify_time'], # 通知时间')
                'notify_type': pay_result['notify_type'], # 通知类型')
                'notify_id': pay_result['notify_id'], # 通知校验ID')
                'app_id': pay_result['app_id'], # 应用Id')
                'charset': pay_result['charset'], # 编码格式')
                'version': pay_result['version'], # 接口版本')
                'sign_type': pay_result['sign_type'], # 签名类型')
                'sign': pay_result['sign'], # 签名')
                'trade_no': pay_result['trade_no'], # 支付宝交易号')
                'out_trade_no': pay_result['out_trade_no'], # 商户订单号')
                'trade_status': pay_result['trade_status'], # 交易状态')
                'total_amount': pay_result['total_amount'], # 订单金额')
                'receipt_amount': pay_result['receipt_amount'], # 实收金额')
                'buyer_pay_amount': pay_result['buyer_pay_amount'], # 付款金额')
                'gmt_create': pay_result['gmt_create'], # 交易创建时间')
                'gmt_payment': pay_result['gmt_payment'], # 交易付款时间')
                'gmt_close': pay_result.get('gmt_close'), # 交易结束时间')
                'passback_params': pay_result['passback_params'], # 回传参数')

                'order_ids': [(6, 0, [order.id])],
            })

        def create_long_pay_record():
            return long_pay_record_obj.create({
                'POSID': pay_result.get('POSID'),
                'BRANCHID': pay_result.get('BRANCHID'),
                'ORDERID': pay_result.get('ORDERID'),
                'PAYMENT': pay_result.get('PAYMENT'),
                'CURCODE': pay_result.get('CURCODE'),
                'REMARK1': pay_result.get('REMARK1'),
                'REMARK2': pay_result.get('REMARK2'),
                'ACC_TYPE': pay_result.get('ACC_TYPE'),
                'SUCCESS': pay_result.get('SUCCESS'),
                'TYPE': pay_result.get('TYPE'),
                'REFERER': pay_result.get('REFERER'),
                'CLIENTIP': pay_result.get('CLIENTIP'),
                'ACCDATE': pay_result.get('ACCDATE'),
                'USRMSG': pay_result.get('USRMSG'),
                'INSTALLNUM': pay_result.get('INSTALLNUM'),
                'ERRMSG': pay_result.get('ERRMSG'),
                'USRINFO': pay_result.get('USRINFO'),
                'DISCOUNT': pay_result.get('DISCOUNT'),
                'SIGN': pay_result.get('SIGN'),

                'order_ids': [(6, 0, [order.id])],
            })



        order_obj = self.env['sale.order']  # 订单
        weixin_pay_record_obj = self.env['his.weixin_pay_record']  # 微信支付记录
        alipay_record_obj = self.env['his.alipay_record']  # 支付宝支付记录
        product_obj = self.env['product.template'] # 产品
        product_category_obj = self.env['product.category'] # 产品分类
        refund_apply_obj = self.env['his.refund_apply'].sudo()  # 退款申请
        long_pay_record_obj = self.env['his.long_pay_record'].sudo()  # 龙支付记录

        data = json.loads(message.payload)
        pay_method = data['pay_method']  # 支付方式
        pay_result = data['pay_result']  # 支付结果
        order_id = data['order_id']  # 订单外网id
        partner_id = data['partner_id'] # 患者
        amount = data['amount']  # 充值金额
        recharge_type = data['recharge_type']  # 充值类型

        # 创建订单
        order = create_order()

        # 创建支付记录
        pay_record = None # 支付记录
        if pay_method == 'weixin':
            pay_record = create_weixin_pay_record()
        if pay_method == 'alipay':
            pay_record = create_alipay_record()
        if pay_method == 'longpay':
            pay_record = create_long_pay_record()

        result = {
            'order_id': order_id,  # 订单外网id
            'order_internal_id': order.id,  # 订单内部ID
            'pay_record_internal_id': pay_record.id,  # 支付记录内部ID,
            'commit_his_state': '1'  # 提交HIS状态
        }

        # 提交HIS
        try:
            res = self.env['his.interface'].recharge_commit_his(order) # tran_flow医院结算流水号
            pay_record.tran_flow = res['tran_flow']
            order.write({
                'commit_his_state': '1',
                'tran_flow': res['tran_flow']
            })
            result.update({
                'mz_balance': res['mz_balance'],  # 门诊帐户余额
                'zy_balance': res['zy_balance'],  # 住院帐户余额
            })
        except Exception, e:
            _logger.error(u'充值提交HIS错误')
            _logger.error(e.message)

            # 修改订单信息
            order.write({
                'commit_his_state': '0',
                'commit_his_error_msg': e.message
            })
            # 创建退款申请
            res = {
                'visit_partner_id': partner_id,
                'pay_method': order.pay_method,
                'amount_total': order.amount_total,
                'order_ids': [(6, 0, [order.id])],
                'state': 'draft',
                'order_type': order.order_type,
                'reason': '充值提交HIS发生错误'
            }
            if order.pay_method == 'weixin':
                res.update({
                    'weixin_pay_ids': [(6, 0, [pay_record.id])],
                    'transaction_id': pay_record.transaction_id
                })
            if order.pay_method == 'alipay':
                res.update({
                    'alipay_ids': [(6, 0, [pay_record.id])],
                    'trade_no': pay_record.trade_no
                })
            if order.pay_method == 'longpay':
                res.update({
                    'long_pay_record_ids': [(6, 0, [pay_record.id])],
                    'trade_no': pay_record.ORDERID
                })

            refund_apply = refund_apply_obj.create(res)
            # 修改通知消息
            message.refund_apply_id = refund_apply.id

            result.update({
                'refund_apply_internal_id': refund_apply.id,  # 退款申请内部ID
                'commit_his_error_msg': e.message,  # 提交HIS错误信息
                'commit_his_state': '0',  # 提交HIS状态
            })

        return message.source_topic, {
            'action': 'recharge_done',
            'data': result
        }

    @api.model
    def inoculation_appointment(self, message):
        """预防接种预约
            APP根据新生儿接种医院发送MQTT消息直接向内网ODOO预约,且等待直到接收到相同动作的MQTT消息，后进行支付处理或展示预约成功页面。
            内网收到消息处理完成后，向外网推送预约信息，同时返回相同动作的MQTT消息到APP
            外网收到内网的MQTT消息后，记录到数据库中
        """
        def create_reserve_record():

            return reserve_record_obj.create({
                'partner_id': partner_id,  # 患者
                'reserve_date': register_source.date,  # 预约日期
                'department_id': register_source.department_id.id,  # 科室
                'employee_id': False,  # 医生
                'shift_type_id': register_source.shift_type_id.id,  # 班次
                'register_source_id': source_id,  # 号源
                'type': 'inoculation', # 预约类别s
                'order_id': False,  # 订单
                'state': 'draft',  # 状态
            })

        reserve_record_obj = self.env['his.reserve_record']  # 预约记录
        register_source_obj = self.env['his.register_source'] # 号源
        register_plan_obj = self.env['his.register_plan']  # 挂号记划表
        inoculation_personal_schedule_obj = self.env['his.inoculation_personal_schedule'] # 个人接种计划

        data = json.loads(message.payload)
        source_id = data['source_id'] # 号源ID
        partner_id = data['partner_id'] # 新生儿内部ID
        cycle_id = data['cycle_id'] # 接种周期内部ID

        register_source = register_source_obj.browse(source_id)  # 号源

        # 创建预约记录
        reserve_record = create_reserve_record()
        # 修改号源状态
        register_source_obj.appointment_register(register_source.id) # 号源状态改为已经预约
        # 修改挂号记录表
        register_plan = register_plan_obj.search([('medical_date', '=', register_source.date), ('department_id', '=', register_source.department_id.id), ('employee_id', '=', False)])
        for line in register_plan.line_ids:
            if line.time_point_name == register_source.time_point_name:
                line.write({
                    'partner_id': partner_id,
                    'source': 'app',
                    'register_time': datetime.now().strftime(DATE_FORMAT),
                    'reserve_time_point_name': register_source.time_point_name
                })
                reserve_record.reserve_sort = line.medical_sort  # 预约顺序号
                break

        # 向外网发送MQTT消息
        payload = {
            'action': 'inoculation_appointment',
            'data': {
                'partner_id': partner_id, # 患者内部ID
                'source_id': source_id, # 号源内部ID
                'reserve_record_id': reserve_record.id, # 预约记录内部ID
                'reserve_sort': reserve_record.reserve_sort,  # 预约顺序号
                # 'cycle_id': cycle_id, # 接种周期内部ID
            }
        }
        self.publish(config['extranet_topic'], payload)
        # TODO 接种计划与预约记录关联
        # inoculation_personal_schedule_obj.search([('partner_id', '=', partner_id), ('cycle_id', '=', cycle_id)]).write({
        #     'reserve_record_id': reserve_record.id
        # })
        # TODO 创建就医流程

        return message.source_topic, {
            'action': 'inoculation_appointment',
            'data': {
                'reserve_record_id': reserve_record.id,
                'reserve_date': register_source.date,  # 预约日期
                'reserve_sort': reserve_record.reserve_sort, # 预约顺序号
                'department': register_source.department_id.name, # 预约科室
                'location': register_source.department_id.location or '', # 科室位置
                'time_point_name': register_source.time_point_name, # 预约时间点
            }
        }

    @api.model
    def inoculation_payed(self, message):
        """预防接种支付成功，通知内网"""
        def create_order():
            """创建订单"""
            res = order_obj.create({
                'partner_id': appointment_record.partner_id.id,
                'pay_method': pay_method,
                'order_type': 'inoculation'
            })
            for product in product_obj.browse(product_ids):
                order_line_obj.create({
                    'order_id': res.id,
                    'product_id': product.product_variant_id.id,
                    'name': product.name,
                    'product_uom_qty': 1,
                    'product_uom': product.uom_id.id,
                    'price_unit': product.list_price
                })

            return res

        def create_weixin_pay_record():
            """创建微信支付记录"""
            return weixin_pay_record_obj.create({
                'return_code': pay_result.get('return_code'), # 返回状态码
                'return_msg': weixin_pay_info.get('return_msg'), # 返回信息
                'appid': weixin_pay_info.get('appid'), # 应用ID
                'mch_id': weixin_pay_info.get('mch_id'), # 商户号
                'device_info': weixin_pay_info.get('device_info'), # 设备号
                'nonce_str': weixin_pay_info.get('nonce_str'), # 随机字符串
                'sign': weixin_pay_info.get('sign'), # 签名
                'result_code': weixin_pay_info.get('result_code'), # 业务结果
                'err_code': weixin_pay_info.get('err_code'), # 错误代码
                'err_code_des': weixin_pay_info.get('err_code_des'), # 错误代码描述
                'openid': weixin_pay_info.get('openid'), # 用户标识
                'is_subscribe': weixin_pay_info.get('is_subscribe'), # 是否关注公众账号
                'trade_type': weixin_pay_info.get('trade_type'), # 交易类型
                'bank_type': weixin_pay_info.get('bank_type'), # 付款银行
                'total_fee': weixin_pay_info.get('total_fee'), # 总金额
                'fee_type': weixin_pay_info.get('fee_type'), # 货币种类
                'cash_fee': weixin_pay_info.get('cash_fee'), # 现金支付金额
                'cash_fee_type': weixin_pay_info.get('cash_fee_type'), # 现金支付货币类型
                'transaction_id': weixin_pay_info.get('transaction_id'), # 微信支付订单号
                'out_trade_no': weixin_pay_info.get('out_trade_no'), # 商户订单号
                'attach': weixin_pay_info.get('attach'), # 商家数据包
                'time_end': weixin_pay_info.get('time_end'), # 支付完成时间
                'order_id': order.id,
            })

        def create_alipay_record():
            """创建支付宝支付记录"""
            # TODO
            return alipay_record_obj.create({
                'out_trade_no': alipay_info['out_trade_no'],
                'trade_no': alipay_info['trade_no'],
                'app_id': alipay_info['app_id'],
                'total_amount': alipay_info['total_amount'],
                'seller_id': alipay_info['seller_id'],
                'msg': alipay_info['msg'],
                'charset': alipay_info['charset'],
                'timestamp': alipay_info['timestamp'],
                'is_success': alipay_info['is_success'],
                'code': alipay_info['code'],

                'order_id': order.id
            })

        order_obj = self.env['sale.order']  # 订单
        order_line_obj = self.env['sale.order.line']  # 订单明细
        reserve_record_obj = self.env['his.reserve_record']  # 预约记录
        product_obj = self.env['product.template'] # 产品
        weixin_pay_record_obj = self.env['his.weixin_pay_record']  # 微信支付记录
        alipay_record_obj = self.env['his.alipay_record']  # 支付宝支付记录

        data = json.loads(message.payload)

        appointment_record_id = data['appointment_record_id'] # 预约记录内部ID
        pay_method = data['pay_method'] # 支付方式
        product_ids = data['product_ids'] # 收费项目内网ID
        order_id = data['order_id']  # 外网订单ID
        weixin_pay_info = data.get('weixin')  # 微信支付信息
        alipay_info = data.get('alipay')  # 支付宝支付信息


        appointment_record = reserve_record_obj.browse(appointment_record_id) # 预约记录

        # 创建订单
        order = create_order()

        # 预约记录与订单关联
        appointment_record.order_id = order.id

        # 创建支付记录
        weixin_pay_record_id = False
        alipay_record_id = False
        if pay_method == 'weixin':
            weixin_pay_record = create_weixin_pay_record()
            weixin_pay_record_id = weixin_pay_record.id

        if pay_method == 'alipay':
            alipay_record = create_alipay_record()
            alipay_record_id = alipay_record.id

        return message.source_topic, {
            'action': 'appointment_register',
            'data': {
                'order_id': order_id,
                'weixin_internal_id': weixin_pay_record_id,
                'alipay_internal_id': alipay_record_id,
                'order_internal_id': order.id
            }
        }

    @api.model
    def app_sign_in(self, message):
        """手机签到 by liuchang"""
        treatment_process_line_obj = self.env['hrp.treatment_process_line']
        # register_obj = self.env['his.register']
        queue_obj = self.env['hrp.queue']

        data = json.loads(message.payload)

        treatment_process_line_id = data['treatment_process_line_id']

        treatment_process_line = treatment_process_line_obj.search([('id', '=', treatment_process_line_id)])

        if not treatment_process_line:
            return message.source_topic, {
                'action': 'app_sign_in',
                'data': {'state': 0, 'msg': '流程错误'}
            }

        # if not treatment_process_line.receipt_no:
        #     return message.source_topic, {
        #         'action': 'app_sign_in',
        #         'data': {'state': 0, 'msg': '暂不能签到'}
        #     }
        #
        # # 查询病人挂号记录
        # register = register_obj.search([('partner_id', '=', treatment_process_line.partner_id.id), ('receipt_no', '=', treatment_process_line.receipt_no)], limit=1)
        #
        # if not register:
        #     return message.source_topic, {
        #         'action': 'app_sign_in',
        #         'data': {'state': 0, 'msg': '未找到病人挂号记录'}
        #     }
        #
        # if not register.total_queue_id:
        #     return message.source_topic, {
        #         'action': 'app_sign_in',
        #         'data': {'state': 0, 'msg': '没有队列信息'}
        #     }

        if not treatment_process_line.queue_id:
            return message.source_topic, {
                'action': 'app_sign_in',
                'data': {'state': 0, 'msg': '不能签到'}
            }

        # 签到
        arg = {
            'code': 'app',
            'state': 1,
            'id': treatment_process_line.queue_id.id
        }
        res = queue_obj.queue_state_change(user=None, arg=arg)
        if not res['state']:
            return message.source_topic, {
                'action': 'app_sign_in',
                'data': {'state': 0, 'msg': res['desc']}
            }

        return message.source_topic, {
            'action': 'app_sign_in',
            'data': {'state': 1, 'msg': '签到成功'}
        }

    @api.model
    def cancel_reserve_record(self, message):
        """取消预约挂号"""
        reserve_record_obj = self.env['his.reserve_record']  # 预约记录
        refund_apply_obj = self.env['his.refund_apply'].sudo()  # 退款申请
        register_plan_obj = self.env['his.register_plan'] # 队列计划
        register_plan_line_obj = self.env['his.register_plan_line'] # 队列计划明细

        data = json.loads(message.payload)
        reserve_id = data['reserve_id'] # 预约记录内部ID

        reserve_record = reserve_record_obj.browse(reserve_id)
        # 取消订单
        order = reserve_record.order_id
        order.action_cancel()
        # 更新预约记录
        reserve_record.write({
            'state': 'cancel',
            'cancel_type': '1', # 用户取消
        })
        refund_apply_internal_id = False
        if order.pay_method not in ['free', 'coupon']:
            # 创建退款申请
            res = {
                'visit_partner_id': reserve_record.partner_id.id,
                'pay_method': order.pay_method,
                'amount_total': order.amount_total,
                'order_ids': [(6, 0, [order.id])],
                'state': 'draft',
                'order_type': order.order_type,
                'reason': '取消预约挂号'
            }
            if order.pay_method == 'weixin':
                res.update({
                    'weixin_pay_ids': [(6, 0, [weixin_pay.id for weixin_pay in order.weixin_pay_ids])],
                    'transaction_id': order.weixin_pay_ids[0].transaction_id
                })
            if order.pay_method == 'alipay':
                res.update({
                    'alipay_ids': [(6, 0, [alipay.id for alipay in order.alipay_ids])],
                    'trade_no': order.alipay_ids[0].trade_no
                })
            refund_apply = refund_apply_obj.create(res)
            refund_apply_internal_id = refund_apply.id
        # 更改号源状态
        reserve_record.register_source_id.state = '0'
        # 修改队列计划
        register_plan = register_plan_obj.search([('medical_date', '=', reserve_record.reserve_date), ('department_id', '=', reserve_record.department_id.id), ('employee_id', '=', reserve_record.employee_id.id)])
        if register_plan:
            register_plan_line = register_plan_line_obj.search([('register_plan_id', '=', register_plan.id), ('time_point_name', '=', reserve_record.register_source_id.time_point_name)])
            if register_plan_line:
                register_plan_line.write({
                    'partner_id': False,
                    'source': False,
                    'register_time': False,
                    'reserve_time_point_name': False
                })
        # 返回到外网
        return message.source_topic, {
            'action': 'cancel_reserve_record',
            'data': {
                'refund_apply_internal_id': refund_apply_internal_id, # 退款申请内部ID
                'refund_apply_id': data['refund_apply_id'], # 退款申请外部ID
            }
        }

    @api.model
    def query_refund_result(self, message):
        """退款申请查询完成"""
        refund_apply_obj = self.env['his.refund_apply'] # 退款申请

        data = json.loads(message.payload)

        refund_apply_id = data['refund_apply_id'] # 退款申请内部ID
        refund_apply = refund_apply_obj.browse(refund_apply_id) # 退款申请

        # 修改状况态
        refund_apply.write({
            'state': 'done',
            'refund_time': datetime.now().strftime(DATETIME_FORMAT)
        })

        # 修改订单状态
        for order in refund_apply.order_ids:
            order.write({
                'is_refund': True,
                'refund_time': datetime.now().strftime(DATETIME_FORMAT)
            })

        # 修改支付记录的退款信息
        if refund_apply.alipay_ids:
            result = data['result']
            for alipay in refund_apply.alipay_ids:
                alipay.write({
                    'refund_code': result['code'],
                    'refund_msg': result['msg'],
                    'is_refund': True,
                    'refund_time': datetime.now().strftime(DATETIME_FORMAT)
                })

        if refund_apply.weixin_pay_ids:
            result = data['result']
            for weixin_pay in refund_apply.weixin_pay_ids:
                weixin_pay.write({
                    'is_refund': True,
                    'refund_time': datetime.now().strftime(DATETIME_FORMAT),
                    'refund_code': result['result_code'],
                    'refund_msg': result['return_msg'],
                })

    @api.model
    def get_patient_in_hospital(self, message):
        """查询病人是否在院"""
        partner_id = json.loads(message.payload)['partner_id']
        partner = self.env['res.partner'].browse(partner_id)
        sql = u'''
        SELECT
            to_char(T.入院时间, 'yyyy-mm-dd hh24:mi:ss') in_hospital_datetime,
            T.在院 in_hospital
        FROM
            病人信息 T
        WHERE
            T.病人ID=:0
        '''
        ora_obj = Ora()
        values = ora_obj.query(sql, [partner.his_id])

        in_hospital = 0
        if values and values[0]['in_hospital']:
            in_hospital = 1


        # 返回到外网
        return message.source_topic, {
            'action': 'get_patient_in_hospital',
            'data': {
                'in_hospital': in_hospital, # 退款申请内部ID
            }
        }

    @api.model
    def service_pay_done(self, message):
        """便民服务支付完成, 外网处理完成后向内网发送MQTT接口"""
        def create_order():
            """创建订单"""
            order_lines = [(0, 0, {
                'product_id': fee.product_id.product_variant_id.id,
                'name': fee.product_id.name,
                'product_uom_qty': fee.scale,
                'price_unit': fee.list_price,
                'product_uom': fee.uom_id.id,
                'tax_id': False,
            }) for detail in convenient_item.package_detail_ids for fee in detail.fee_ids]

            order_res = order_obj.create({
                'partner_id': partner_id,  # 患者ID,
                'pay_method': pay_method,  # 支付方式,
                'order_type': 'service',
                'order_line': order_lines,
                'state': 'sale',
                'convenient_item_id': convenient_item.id,  # 便民服务项目ID
            })

            return order_res

        def create_weixin_pay_record():
            """创建微信支付记录"""
            return weixin_pay_record_obj.create({
                'return_code': pay_result.get('return_code'), # 返回状态码
                'return_msg': pay_result.get('return_msg'), # 返回信息
                'appid': pay_result.get('appid'), # 应用ID
                'mch_id': pay_result.get('mch_id'), # 商户号
                'device_info': pay_result.get('device_info'), # 设备号
                'nonce_str': pay_result.get('nonce_str'), # 随机字符串
                'sign': pay_result.get('sign'), # 签名
                'result_code': pay_result.get('result_code'), # 业务结果
                'err_code': pay_result.get('err_code'), # 错误代码
                'err_code_des': pay_result.get('err_code_des'), # 错误代码描述
                'openid': pay_result.get('openid'), # 用户标识
                'is_subscribe': pay_result.get('is_subscribe'), # 是否关注公众账号
                'trade_type': pay_result.get('trade_type'), # 交易类型
                'bank_type': pay_result.get('bank_type'), # 付款银行
                'total_fee': pay_result.get('total_fee'), # 总金额
                'fee_type': pay_result.get('fee_type'), # 货币种类
                'cash_fee': pay_result.get('cash_fee'), # 现金支付金额
                'cash_fee_type': pay_result.get('cash_fee_type'), # 现金支付货币类型
                'transaction_id': pay_result.get('transaction_id'), # 微信支付订单号
                'out_trade_no': pay_result.get('out_trade_no'), # 商户订单号
                'attach': pay_result.get('attach'), # 商家数据包
                'time_end': pay_result.get('time_end'), # 支付完成时间
                'order_ids': [(6, 0, [order.id])],
            })

        def create_alipay_record():
            """创建支付宝支付记录"""
            return alipay_record_obj.create({
                'notify_time': pay_result['notify_time'], # 通知时间')
                'notify_type': pay_result['notify_type'], # 通知类型')
                'notify_id': pay_result['notify_id'], # 通知校验ID')
                'app_id': pay_result['app_id'], # 应用Id')
                'charset': pay_result['charset'], # 编码格式')
                'version': pay_result['version'], # 接口版本')
                'sign_type': pay_result['sign_type'], # 签名类型')
                'sign': pay_result['sign'], # 签名')
                'trade_no': pay_result['trade_no'], # 支付宝交易号')
                'out_trade_no': pay_result['out_trade_no'], # 商户订单号')
                'trade_status': pay_result['trade_status'], # 交易状态')
                'total_amount': pay_result['total_amount'], # 订单金额')
                'receipt_amount': pay_result['receipt_amount'], # 实收金额')
                'buyer_pay_amount': pay_result['buyer_pay_amount'], # 付款金额')
                'gmt_create': pay_result['gmt_create'], # 交易创建时间')
                'gmt_payment': pay_result['gmt_payment'], # 交易付款时间')
                'gmt_close': pay_result.get('gmt_close'), # 交易结束时间')
                'passback_params': pay_result['passback_params'], # 回传参数')

                'order_ids': [(6, 0, [order.id])],
            })

        def create_long_pay_record():
            return long_pay_record_obj.create({
                'POSID': pay_result.get('POSID'),
                'BRANCHID': pay_result.get('BRANCHID'),
                'ORDERID': pay_result.get('ORDERID'),
                'PAYMENT': pay_result.get('PAYMENT'),
                'CURCODE': pay_result.get('CURCODE'),
                'REMARK1': pay_result.get('REMARK1'),
                'REMARK2': pay_result.get('REMARK2'),
                'ACC_TYPE': pay_result.get('ACC_TYPE'),
                'SUCCESS': pay_result.get('SUCCESS'),
                'TYPE': pay_result.get('TYPE'),
                'REFERER': pay_result.get('REFERER'),
                'CLIENTIP': pay_result.get('CLIENTIP'),
                'ACCDATE': pay_result.get('ACCDATE'),
                'USRMSG': pay_result.get('USRMSG'),
                'INSTALLNUM': pay_result.get('INSTALLNUM'),
                'ERRMSG': pay_result.get('ERRMSG'),
                'USRINFO': pay_result.get('USRINFO'),
                'DISCOUNT': pay_result.get('DISCOUNT'),
                'SIGN': pay_result.get('SIGN'),

                'order_ids': [(6, 0, [order.id])],
            })


        order_obj = self.env['sale.order']  # 订单
        weixin_pay_record_obj = self.env['his.weixin_pay_record']  # 微信支付记录
        alipay_record_obj = self.env['his.alipay_record']  # 支付宝支付记录
        refund_apply_obj = self.env['his.refund_apply'].sudo()  # 退款申请
        convenient_item_obj = self.env['his.convenient_item'].sudo() # 便民服务
        long_pay_record_obj = self.env['his.long_pay_record'].sudo()  # 龙支付记录

        data = json.loads(message.payload)
        pay_method = data['pay_method']  # 支付方式
        pay_result = data['pay_result']  # 支付结果
        order_id = data['order_id']  # 订单外网id
        partner_id = data['partner_id'] # 患者
        convenient_item_id = data['convenient_item_id']  # 便民服务项目ID

        convenient_item = convenient_item_obj.browse(convenient_item_id)

        # 创建订单
        order = create_order()

        # 创建支付记录
        pay_record = None # 支付记录
        if pay_method == 'weixin':
            pay_record = create_weixin_pay_record()
        if pay_method == 'alipay':
            pay_record = create_alipay_record()
        if pay_method == 'longpay':
            pay_record = create_long_pay_record()

        result = {
            'order_id': order_id,  # 订单外网id
            'order_internal_id': order.id,  # 订单内部ID
            'pay_record_internal_id': pay_record.id,  # 支付记录内部ID,
            'commit_his_state': '1'  # 提交HIS状态
        }

        # 提交HIS
        try:
            res = self.env['his.interface'].service_commit_his(order) # tran_flow医院结算流水号
            pay_record.tran_flow = res['tran_flow']
            order.write({
                'commit_his_state': '1',
                'tran_flow': res['tran_flow']
            })
        except Exception, e:
            _logger.error(u'充值提交HIS错误')
            _logger.error(e.message)

            # 修改订单信息
            order.write({
                'commit_his_state': '0',
                'commit_his_error_msg': e.message
            })
            # 创建退款申请
            res = {
                'visit_partner_id': partner_id,
                'pay_method': order.pay_method,
                'amount_total': order.amount_total,
                'order_ids': [(6, 0, [order.id])],
                'state': 'draft',
                'order_type': order.order_type,
                'reason': '划价提交HIS发生错误'
            }
            if order.pay_method == 'weixin':
                res.update({
                    'weixin_pay_ids': [(6, 0, [pay_record.id])],
                    'transaction_id': pay_record.transaction_id
                })
            if order.pay_method == 'alipay':
                res.update({
                    'alipay_ids': [(6, 0, [pay_record.id])],
                    'trade_no': pay_record.trade_no
                })
            if order.pay_method == 'longpay':
                res.update({
                    'long_pay_record_ids': [(6, 0, [pay_record.id])],
                    'trade_no': pay_record.ORDERID
                })


            refund_apply = refund_apply_obj.create(res)
            # 修改通知消息
            message.refund_apply_id = refund_apply.id

            result.update({
                'refund_apply_internal_id': refund_apply.id,  # 退款申请内部ID
                'commit_his_error_msg': e.message,  # 提交HIS错误信息
                'commit_his_state': '0',  # 提交HIS状态
            })

        return message.source_topic, {
            'action': 'service_pay_done',
            'data': result
        }


