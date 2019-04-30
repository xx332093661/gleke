# coding: utf-8
import string
import urllib
import urllib2
import uuid
from functools import wraps
import re
import xmltodict
from dateutil.relativedelta import relativedelta

from odoo.http import request
from odoo import http
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from ..models.emqtt import Emqtt
from odoo.tools import config

from ..models.weixin_pay_interface import UnifiedOrder_pub, Wxpay_server_pub
from alipay import AliPay
import get_distance

import logging
import random
import json
import time
import traceback

_logger = logging.getLogger(__name__)


def interface_wraps(func):
    """接口包装"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        _logger.info(u'%s收到数据:%s', func.func_name, json.dumps(request.jsonrequest, ensure_ascii=False, encoding='utf8', indent=4))

        # 令牌验证
        if func.func_name not in ['start', 'startapp']:
            if not request.env['his.app_token'].sudo().validate_token(request.jsonrequest.get('mac'), request.jsonrequest.get('token')):
                result = {'state': 0, 'msg': '非法访问'}
                _logger.info(u'%s返回数据:%s', func.func_name, json.dumps(result, ensure_ascii=False, encoding='utf8'))
                return result

        result = func(self, *args, **kwargs)
        _logger.info(u'%s返回数据:%s', func.func_name, json.dumps(result, ensure_ascii=False, encoding='utf8', indent=4))
        return result

    return wrapper


def check_mobile(mobile):
    """验证手机号码"""
    mobile_pattern_str = config['mobile_pattern_str'] # 手机号码匹配字符串 0\d{2,3}\d{7,8}$|^1[358]\d{9}$|^147\d{8}

    phone_pattern = re.compile(r'^' + mobile_pattern_str + '$')
    phone_group = phone_pattern.match(mobile)
    if not phone_group:
        return False

    return True


def validate_date(date):
    try:
        datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
    except ValueError:
        return False
    return True


def check_identity(identity_no):
    """验证身份证"""
    # area_dict = {11: "北京", 12: "天津", 13: "河北", 14: "山西", 15: "内蒙古", 21: "辽宁", 22: "吉林", 23: "黑龙江", 31: "上海", 32: "江苏",
    #              33: "浙江", 34: "安徽", 35: "福建", 36: "江西", 37: "山东", 41: "河南", 42: "湖北", 43: "湖南", 44: "广东", 45: "广西",
    #              46: "海南", 50: "重庆", 51: "四川", 52: "贵州", 53: "云南", 54: "西藏", 61: "陕西", 62: "甘肃", 63: "青海", 64: "新疆",
    #              71: "台湾", 81: "香港", 82: "澳门", 91: "外国"}
    #
    # id_code_list = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]  # 前17位号码加权因子
    # check_code_list = [1, 0, 'X', 9, 8, 7, 6, 5, 4, 3, 2]  # 验证位
    #
    # if len(identity_no) != 18:
    #     return False
    #
    # if not re.match(r"^\d{17}(\d|X|x)$", identity_no):
    #     return False
    #
    # if int(identity_no[0:2]) not in area_dict:
    #     return False
    #
    # try:
    #     datetime.strptime('%s-%s-%s' % (identity_no[6:10], identity_no[10:12], identity_no[12:14]), '%Y-%m-%d')
    # except ValueError as ve:
    #     return False
    #
    # if str(check_code_list[sum([a * b for a, b in zip(id_code_list, [int(a) for a in identity_no[0:-1]])]) % 11]) != \
    #         identity_no.upper()[-1]:
    #     return False

    return True


class AppInterface(http.Controller):
    """app接口"""

    @http.route('/app/start', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def start(self):
        """app运行"""
        def get_no_condition_company():
            """当坐标不满足条件时的所处医院"""
            prev_company_id = request.jsonrequest['company_id']  # 上一次所处医院
            if prev_company_id:
                return prev_company_id

            if companys:
                return companys[0]['id']

            return 0


        def get_company():
            """根据医院坐标和当前坐标计算当前所处医院"""
            coordinate = request.jsonrequest['coordinate'] # 当前GPS坐标
            if not coordinate:
                return get_no_condition_company()

            longitude = coordinate['longitude'] # 经度
            latitude = coordinate['latitude'] # 纬度
            if not longitude or not latitude:
                return get_no_condition_company()

            # 当前点
            point = get_distance.Point()
            point.lat = latitude
            point.lng = longitude

            res = []
            for com in company_obj.search([('id', '!=', 1)]):
                com_point = get_distance.Point()
                com_point.lat = com.longitude
                com_point.lng = com.longitude

                distance = get_distance.get_distance(point, com_point) # 公司坐标点
                if distance <= com.range:
                    res.append({
                        'company_id': com.id,
                        'distance': distance
                    })


            if not res:
                return get_no_condition_company()

            res = sorted(res, key=lambda x: x['distance'])
            return res[0]['company_id']


        company_obj = request.env['res.company'].sudo()
        app_function_obj = request.env['hrp.app_function'].sudo()
        app_token_obj = request.env['his.app_token'].sudo()


        # 产生动态令牌
        identify = str(uuid.uuid1())
        token = ''.join(random.sample(string.ascii_letters + string.digits, random.randint(8, 32)))
        app_token_obj.create({
            'mac': identify,
            'token': token,
        })

        # 获取所有医院
        companys = [
            {
                'id': company.id,
                'name': company.name,
                'topic': company.topic,
                'features': [{'code': app_function.code} for app_function in company.app_function_ids]
            } for company in company_obj.search([('id', '!=', 1), ('state', '=', '1')])]

        # 根据坐标，计算出所在医院，如果计算不出来，返回上传入参数company_id的值
        company_id = get_company()


        # APP所有功能
        features = [{'code': app_function.code} for app_function in app_function_obj.search([])]

        # 外网ODOO主题
        external_topic = config['topic']

        # 广播APP的动态令牌
        msg = {
            'action': 'app_start',
            'data': {
                'mac': identify,
                'token': token,
            }
        }
        Emqtt.publish('public', msg)

        # 返回结果
        result = {
            'companys': companys,
            'company_id': company_id,
            'features': features,
            'identify': identify,
            'token': token,
            'mqtt_setting': {
                'ip': config.get('emqtt_host'),
                'port': config.get('emqtt_port'),
                'username': config.get('emqtt_user'),
                'password': config.get('emqtt_pwd')
            },
            'external_topic': external_topic,
        }

        return {'state': 1, 'data': result}


    @http.route('/app/startapp', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def startapp(self):
        """app运行(外部)"""

        def get_no_condition_company():
            """当坐标不满足条件时的所处医院"""
            prev_company_id = request.jsonrequest['company_id']  # 上一次所处医院
            if prev_company_id:
                return prev_company_id

            if companys:
                return companys[0]['id']

            return 0

        def get_company():
            """根据医院坐标和当前坐标计算当前所处医院"""
            coordinate = request.jsonrequest['coordinate']  # 当前GPS坐标
            if not coordinate:
                return get_no_condition_company()

            longitude = coordinate['longitude']  # 经度
            latitude = coordinate['latitude']  # 纬度
            if not longitude or not latitude:
                return get_no_condition_company()

            # 当前点
            point = get_distance.Point()
            point.lat = latitude
            point.lng = longitude

            res = []
            for com in company_obj.search([('id', '!=', 1)]):
                com_point = get_distance.Point()
                com_point.lat = com.longitude
                com_point.lng = com.longitude

                distance = get_distance.get_distance(point, com_point)  # 公司坐标点
                if distance <= com.range:
                    res.append({
                        'company_id': com.id,
                        'distance': distance
                    })

            if not res:
                return get_no_condition_company()

            res = sorted(res, key=lambda x: x['distance'])
            return res[0]['company_id']

        company_obj = request.env['res.company'].sudo()
        app_token_obj = request.env['his.app_token'].sudo()

        # 产生动态令牌
        identify = str(uuid.uuid1())
        token = ''.join(random.sample(string.ascii_letters + string.digits, random.randint(8, 32)))
        app_token_obj.create({
            'mac': identify,
            'token': token,
        })

        # 获取所有医院
        companys = [
            {
                'id': company.id,
                'name': company.name
            } for company in company_obj.search([('id', '!=', 1), ('state', '=', '1')])]

        # 根据坐标，计算出所在医院，如果计算不出来，返回上传入参数company_id的值
        company_id = get_company()

        # 广播APP的动态令牌
        msg = {
            'action': 'app_start',
            'data': {
                'mac': identify,
                'token': token,
            }
        }
        Emqtt.publish('public', msg)

        # 返回结果
        result = {
            'companys': companys,
            'company_id': company_id,
            'identify': identify,
            'token': token,
        }

        return {'state': 1, 'data': result}

    @http.route('/app/register', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def register(self):
        """用户注册"""
        verify_code_record_obj = request.env['hrp.verify_code_record'].sudo()
        users_obj = request.env['res.users'].sudo()

        data = request.jsonrequest['data']

        phone = data['phone']
        password = data['password']
        verify_code = data['verify_code']

        # 验证验证码
        if not verify_code_record_obj.verify(phone, verify_code):
            return {'state': 0, 'msg': '验证码无效'}

        # 用户是否存在
        if users_obj.search([('login', '=', phone)]):
            return {'state': 0, 'msg': '该手机号已注册'}

        # 创建用户
        user = users_obj.create({
            'name': phone,
            'login': phone,
            'tz': 'Asia/Shanghai',
            'password': password,
            'groups_id': [(6, 0, [])]
        })
        user.partner_id.write({
            'phone': phone,
            'password': password,
        })

        return {'state': 1, 'msg': '注册成功'}


    @http.route('/app/login', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def login(self):
        """用户登陆"""
        users_obj = request.env['res.users'].sudo()

        data = request.jsonrequest.get('data')

        phone = data.get('phone')
        password = data.get('password')

        user = users_obj.search([('login', '=', phone)])
        if not user:
            return {'state': 0, 'msg': '手机号没有注册'}

        partner = user.partner_id
        if partner.password != password:
            return {'state': 0, 'msg': '密码错误'}
        partners = []
        for relationship in partner.relationship_ids:
            child_data = {
                'id': relationship.partner_id.id,
                'name': relationship.partner_id.name,
                'property': relationship.partner_id.patient_property,
                'phone': relationship.partner_id.phone,
                'sex': relationship.partner_id.gender,
                'identity_no': relationship.partner_id.identity_no,
                'medical_card': relationship.partner_id.medical_card,
                'company_name': relationship.partner_id.work_company,
                'address': relationship.partner_id.address,
                'birth_date': relationship.partner_id.birth_date,
                'inoculation_code': relationship.partner_id.inoculation_code,
                'last_menstruation_day': relationship.partner_id.last_menstruation_day,
                'plan_born_day': relationship.partner_id.plan_born_day,
                'patients': []
            }
            for patient in relationship.partner_id.patient_ids:
                child_data['patients'].append({
                    'company_id': patient.company_id.id,
                    'internal_id': patient.internal_id,
                    'card_no': patient.card_no
                })
            partners.append(child_data)

        res = {
            'partner_id': partner.id,
            'name': partner.name,
            'image': '/web/image/res.partner/%s/image' % partner.id if partner.image else '',
            'mqtt_topic': partner.phone,
            'partners': partners
        }
        return {'state': 1, 'data': res}


    @http.route('/app/forget_password', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def forget_password(self):
        """忘记密码"""
        verify_code_record_obj = request.env['hrp.verify_code_record'].sudo()

        data = request.jsonrequest.get('data')

        phone = data.get('phone')
        password = data.get('password')
        verify_code = data.get('verify_code')

        # 验证验证码
        if not verify_code_record_obj.verify(phone, verify_code):
            return {'state': 0, 'msg': '验证码无效'}

        # 修改密码
        user = request.env['res.users'].sudo().search([('login', '=', phone)])
        if not user:
            return {'state': 0, 'msg': '用户不存在'}

        user.password = password
        user.partner_id.password = password

        return {'state': 1}


    @http.route('/app/change_password', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def change_password(self):
        """修改密码"""
        data = request.jsonrequest['data']

        partner_id = data['partner_id']
        old_password = data['old_password']
        new_password = data['new_password']

        partner = request.env['res.partner'].sudo().browse(partner_id)
        if not partner:
            return {'state': 0, 'msg': '用户不存在'}

        if partner.password != old_password:
            return {'state': 0, 'msg': '原密码错误'}

        partner.password = new_password
        partner.user_ids[0].password = new_password

        return {'state': 1}


    @http.route('/app/change_partner_info', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def change_partner_info(self):
        """修改用户信息"""
        data = request.jsonrequest.get('data')

        partner_id = data.get('partner_id')
        name = data['name']
        sex = data['sex']
        address = data['address']
        company_name = data['company_name']

        partner = request.env['res.partner'].sudo().browse(partner_id)
        if not partner or not partner.user_ids:
            return {'state': 0, 'msg': '用户不存在'}

        partner.write({
            'name': name,
            'gender': sex,
            'address': address,
            'work_company': company_name,
        })
        partner.user_ids[0].name = name

        return {'state': 1}


    # @http.route('/app/relation_exist_patient', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    # @interface_wraps
    # def relation_exist_patient(self):
    #     """关联已存在的就诊人"""
    #     partner_obj = request.env['res.partner'].sudo()
    #
    #     data = request.jsonrequest['data']
    #
    #     phone = data['phone']
    #
    #     partner = partner_obj.search([('phone', '=', phone)], limit=1)
    #     if not partner:
    #         return {'state': 1, 'data': []}
    #
    #     res = [{
    #         'id': partner.id,
    #         'name': partner.name,
    #         'code': partner.code,
    #         'relationship': 'self',
    #     }]
    #
    #     for relationship in partner.relationship_ids:
    #         if relationship.partner_id == partner:
    #             continue
    #
    #         res.append({
    #             'id': relationship.partner_id.id,
    #             'name': relationship.partner_id.name,
    #             'code': relationship.partner_id.code,
    #             'relationship': relationship.relationship,
    #         })
    #
    #     return {'state': 1, 'data': res}


    @http.route('/app/relation_exist_patient', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def relation_exist_patient(self):
        """关联已存在的就诊人"""
        partner_obj = request.env['res.partner'].sudo()
        partner_relationship_obj = request.env['his.partner_relationship'].sudo()

        data = request.jsonrequest['data']
        partner_id = data['partner_id'] # 用户ID

        partner = partner_obj.search([('id', '=', partner_id)])
        if not partner:
            return {'state': 0, 'msg': '客户不存在'}

        if partner_id == data['patient_id']:
            return {'state': 0, 'msg': '不能关联本人'}

        partner_relationship_obj.create({
            'parent_id': partner_id, # 用户ID
            'partner_id': data['patient_id'], # 就诊人ID
            'relationship': data['relation'] # 就诊人与用户关系
        })
        return {'state': 1, 'msg': '添加成功'}



    @http.route('/app/add_patient', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def add_patient(self):
        """添加患者"""
        partner_obj = request.env['res.partner'].sudo()
        partner_relationship_obj = request.env['his.partner_relationship'].sudo()

        data = request.jsonrequest['data']

        # 计算用户是否存在
        partner_id = data['partner_id']  # 当前用户ID
        partner = partner_obj.search([('id', '=', partner_id)])
        if not partner:
            return {'state': 0, 'msg': '用户不存在'}

        # 每个用户最多添加5个就诊人
        # patients = partner_relationship_obj.search([('parent_id', '=', partner_id)])
        # if len(patients) >= 5:
        #     return {'state': 0, 'msg': '最多添加5个就诊人'}

        patient_property = data['patient_property']  # 患者性质
        today = datetime.strptime(datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT), DEFAULT_SERVER_DATE_FORMAT) # 当前日期

        vals = {}
        # 验证新生儿出生日期, 儿童编码是否存在, 接种本条形码是否存在
        if patient_property == 'newborn':
            birth_date = data['birth_date'] # 新生儿出生日期

            if not birth_date:
                return {'state': 0, 'msg': '请填写出生日期'}

            if not validate_date(birth_date):
                return {'state': 0, 'msg': '请填写正确的出生日期'}

            birth_date = datetime.strptime(birth_date, DEFAULT_SERVER_DATE_FORMAT)

            if birth_date > today:
                return {'state': 0, 'msg': '出生日期不得大于当前日期'}

            if relativedelta(today, birth_date).years > 6:
                return {'state': 0, 'msg': '出生日期的值太早了'}

            inoculation_code = data['inoculation_code'] # 儿童编码
            if inoculation_code and partner_obj.search([('inoculation_code', '=', inoculation_code)]):
                return {'state': 0, 'msg': '儿童编码重复'}

            note_code = data.get('note_code') # 接种本条形码
            if note_code and partner_obj.search([('note_code', '=', note_code)]):
                return {'state': 0, 'msg': '接种条形码重复'}

            vals.update({
                'birth_date': data['birth_date'], # 新生儿出生日期
                'inoculation_code': inoculation_code,
                'note_code': note_code,
            })

        # 验证孕妇末次月经日期和预产期
        if patient_property == 'pregnant':
            last_menstruation_day = data['last_menstruation_day'] # 末次月经日期
            plan_born_day = data['plan_born_day'] # 预产期
            if not last_menstruation_day and not plan_born_day:
                return {'state': 0, 'msg': '请填写末次月经日期或预产期'}

            if last_menstruation_day:
                if not validate_date(last_menstruation_day):
                    return {'state': 0, 'msg': '请填写正确的末次月经日期'}

                last_menstruation_date = datetime.strptime(last_menstruation_day, DEFAULT_SERVER_DATE_FORMAT)
                if last_menstruation_date > today:
                    return {'state': 0, 'msg': '末次月经日期不能大于当前日期'}

                if last_menstruation_date < today - timedelta(days=280):
                    return {'state': 0, 'msg': '末次月经日期值太小了'}

                vals.update({
                    'last_menstruation_day': data['last_menstruation_day'], # 末次月经日期
                    'plan_born_day': (last_menstruation_date + timedelta(days=280)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                })

            else:
                if not validate_date(plan_born_day):
                    return {'state': 0, 'msg': '请填写正确的预产期'}

                plan_born_date = datetime.strptime(plan_born_day, DEFAULT_SERVER_DATE_FORMAT)
                if plan_born_date < today:
                    return {'state': 0, 'msg': '预产期不能小于当前日期'}

                if plan_born_date > today + timedelta(days=280):
                    return {'state': 0, 'msg': '预产期值太大了'}

                vals.update({
                    'last_menstruation_day': (plan_born_date - timedelta(days=280)).strftime(DEFAULT_SERVER_DATE_FORMAT), # 末次月经日期
                    'plan_born_day': plan_born_day,
                })

            vals['gender'] = 'female' # 性别

        # 验证孕妇和常规就诊人身份证号
        identity_no = data['identity_no']
        if patient_property in ['pregnant', 'normal']:
            if not identity_no:
                return {'state': 0, 'msg': '请填写身份证号'}

        # 验证身份证号
        if identity_no:
            if not check_identity(identity_no):
                return {'state': 0, 'msg': '请填写正确的身份证'}

            if partner_obj.search([('identity_no', '=', identity_no)]):
                return {'state': 0, 'msg': '身份证号已经存在'}

            vals['identity_no'] = identity_no # 身份证号
            if not vals.get('birth_date'):
                vals['birth_date'] = '%s-%s-%s' % (identity_no[6:10], identity_no[10:12], identity_no[12:14])



        # 验证电话号码
        if data['phone']:
            if not check_mobile(data['phone']):
                return {'state': 0, 'msg': '电话号码错误'}

        if patient_property in ['newborn', 'normal']:
            vals['gender'] = data['sex']  # 性别

        vals.update({
            'patient_property': patient_property, # 就诊人性质
            'name': data['name'],
            'medical_card': data['medical_card'], # 医保卡号
            'company_name': data['company_name'], # 工作单位
            'address': data['address'], # 现住址
            'phone': data['phone'], # 电话号码
            'is_patient': True,
            'customer': False
        })

        # 创建就诊人
        patient = partner_obj.create(vals)
        partner_relationship_obj.create({'relationship': data['relation'], 'parent_id': partner_id, 'partner_id': patient.id}) # 就诊人与用户关联
        request.cr.commit()  # 提交

        # 发送消息通知内网
        msg = {
            'action': 'add_patient',
            'data': {
                'partner_id': patient.id, # 就诊人ID
                'patient_property': patient.patient_property,  # 患者性质
                'name': patient.name, # 姓名
                'gender': patient.gender,  # 性别
                'identity_no': patient.identity_no,  # 身份证号
                'medical_card': patient.medical_card,  # 医保卡号
                'phone': patient.phone, # 电话
                'company_name': patient.work_company, # 工作单位
                'address': patient.address, # 现住址
                'birth_date': patient.birth_date, # 出生日期
                'inoculation_code': getattr(patient, 'inoculation_code', ''), # 儿童编码
                # 'inoculation_code': patient.inoculation_code, # 儿童编码
                # 'note_code': patient.note_code, # 接种本条形码
                'note_code': getattr(patient, 'note_code', ''), # 接种本条形码
                'last_menstruation_day': patient.last_menstruation_day, # 末次月经日期
                'plan_born_day': patient.plan_born_day, # 预产期
            }
        }
        Emqtt.publish('public', msg)

        return {'state': 1, 'data': {'patient_id': patient.id}}



    @http.route('/app/get_verify_code', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_verify_code(self):
        """获取短信验证码"""
        def can_send_sms():
            """根据系统参数短信发送的时间间隔,计算当前用户是否可以发送短信"""

            # 最近一次发送的时间
            verify_code_record = verify_code_record_obj.search([('phone', '=', phone)], limit=1, order='id desc')
            if not verify_code_record:
                return True

            # 短信发送的时间间隔
            sms_send_interval = int(config['sms_send_interval'])

            create_date = datetime.strptime(verify_code_record.create_date, DEFAULT_SERVER_DATETIME_FORMAT)
            if create_date + timedelta(minutes=int(sms_send_interval)) < datetime.now():
                return True

            return False

        def build_sms_signup_data():
            """构建注册验证短信请求参数"""

            parameters = {
                'userid': config['sms_userid'], # 企业id 1113
                'account': config['sms_account'], # 发送用户帐号 shango
                'password': config['sms_password'], # 发送帐号密码 123456
                'mobile': phone, # 全部被叫号码
                'content': sms_content.encode('utf8'), # 发送内容
                'sendTime': '', # 定时发送时间
                'action': 'send',  # 发送任务命令
                'extno': '' # 扩展子号
            }
            parameters = urllib.urlencode(parameters)
            return parameters

        verify_code_record_obj = request.env['hrp.verify_code_record'].sudo()

        data = request.jsonrequest['data']

        phone = data['phone']

        # 手机号码合法性验证
        if not check_mobile(phone):
            return {'state': 0, 'msg': '手机号码错误'}

        # 是否可以发送短信
        if not can_send_sms():
            return {'state': 0, 'msg': '短信发送太频繁'}

        verify_code = random.randint(100000, 999999) # 验证码
        sms_content = u'【GLEKE】注册验证码:%s，请在5分钟内填写。如非本人操作，请忽略本短信。' % verify_code  # 短信内容

        # 发送短信数据
        sms_data = build_sms_signup_data()

        # SMS短信请求
        try:
            sms_request = urllib2.Request(config['sms_gateway'], sms_data) # http://106.3.37.99:7799/sms.aspx
            response = urllib2.urlopen(sms_request)
        except:
            return {'state': 0, 'msg': '发送短信失败,请重试'}

        # 响应数据
        result = response.read()
        response_data = xmltodict.parse(result)
        response.close()

        # 是否发送成功
        success = response_data['returnsms']['returnstatus'].upper() == 'SUCCESS'
        # 创建短信发送记录
        verify_code_record_obj.create({
            'phone': phone,
            'verify_code': verify_code,
            'send_date': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
            'content': sms_content,
            'result': result,
            'success': success
        })

        if success:
            return {'state': 1, 'data': {'verify_code': verify_code}}

        return {'state': 0, 'msg': '发送短信失败，请重试'}


    @http.route('/app/get_departments', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_departments(self):
        """获取科室"""
        department_category_obj = request.env['hrp.department_category'].sudo()
        department_obj = request.env['hr.department'].sudo()

        company_id = request.jsonrequest['data']['company_id']

        result = []

        categorys = department_category_obj.search([('company_id', '=', company_id)])
        if categorys:
            for category in categorys:
                # 科室分类下的排班科室
                departments = [
                    {
                        'department_id': department.id,
                        'department_name': department.name,
                        'pinyin': department.pinyin or ''
                    }for department in department_obj.search([('category_id', '=', category.id), ('is_shift', '=', True), ('is_outpatient', '=', True)])]

                if not departments:
                    continue

                result.append({
                    'category_id': category.id,
                    'category_name': category.name,
                    'departments': departments
                })
        # 无分类
        else:
            departments = [
                {
                    'department_id': department.id,
                    'department_name': department.name,
                    'pinyin': department.pinyin
                } for department in department_obj.search([('company_id', '=', company_id), ('is_shift', '=', True), ('is_outpatient', '=', True)])]
            result.append({
                'category_id': False,
                'category_name': False,
                'departments': departments
            })

        return {'state': 1, 'data': result}


    @http.route('/app/get_doctors', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_doctors(self):
        """根据科室获取医生排班信息"""
        def shift_is_full(schedule_shift1):
            """号是否已挂完"""
            is_full = True
            for register_source in schedule_shift1.register_source_ids:
                if register_source.readonly: # 已过期
                    continue

                if register_source.state == '0': # 待预约
                    is_full = False
                    break

            return is_full

        department_obj = request.env['hr.department'].sudo()
        schedule_shift_obj = request.env['his.schedule_shift'].sudo()
        schedule_department_employee_obj = request.env['his.schedule_department_employee'].sudo()

        department_id = request.jsonrequest['data']['department_id']

        department = department_obj.browse(department_id)
        if not department:
            return {'state': 0, 'msg': '科室不存在'}

        today = (datetime.today() + timedelta(hours=8)).date() # 当前日期
        weeks = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'] # 星期
        result = []

        # 排班班次
        schedule_shifts = schedule_shift_obj.search([('department_id', '=', department_id),
                                          ('schedule_id.date', '>=', today.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                                          ('schedule_id.date', '<=', (today + timedelta(days=department.company_id.appoint_day)).strftime(DEFAULT_SERVER_DATE_FORMAT))])

        # 排班班次按医生分组
        employee_group = {}
        for schedule_shift in schedule_shifts:
            employee_group.setdefault(schedule_shift.employee_id, []).append(schedule_shift)

        for employee in employee_group:
            shifts = [
                {
                    'id': schedule_shift.id, # 班次Id
                    'date': datetime.strptime(schedule_shift.schedule_id.date, DEFAULT_SERVER_DATE_FORMAT).strftime('%m-%d'), # 日期
                    'week': weeks[int(datetime.strptime(schedule_shift.schedule_id.date, DEFAULT_SERVER_DATE_FORMAT).strftime('%w'))], # 星期名称
                    'shift_name': schedule_shift.shift_type_id.name, # 班次名称
                    'is_stop': schedule_shift.is_stop, # 是否停诊
                    'is_full': shift_is_full(schedule_shift), # 号是否已挂完
                }for schedule_shift in employee_group[employee] if not schedule_shift.expired]

            if not shifts:
                continue

            products = schedule_department_employee_obj.search([('department_id', '=', department_id), ('employee_id', '=', employee.id)]).product_ids
            fee = 0 # 总费用
            fee_name_group = {} # 按收据费目分组
            for product in products:
                fee += product.list_price
                fee_name_group.setdefault(product.fee_name, 0)
                fee_name_group[product.fee_name] += product.list_price

            receipt_fee = [{'name': item[0], 'fee': item[1]}for item in fee_name_group.items()]  # 收据费目


            result.append({
                'id': employee.id,  # 医生id
                'image': '/web/image/hr.employee/%s/image' % employee.id if employee.image else '',  # 头像,
                'name': employee.name,  # 姓名,
                'title': employee.title or '',  # 职务,
                'good_at': employee.good_at or '',  # 擅长,
                'introduction': employee.introduction or '',  # 简介,
                'write_date': datetime.strptime(employee.write_date, DEFAULT_SERVER_DATETIME_FORMAT).strftime('%Y%m%d%H%M%S'),  # 修改日期,
                'fee': fee,  # 总费用,
                'receipt_fee': receipt_fee, # 收据费目
                'shifts': shifts
            })

        return {'state': 1, 'data': result}


    @http.route('/app/get_doctors2', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_doctors2(self):
        """根据科室获取医生排班信息"""

        department_obj = request.env['hr.department'].sudo()
        schedule_shift_obj = request.env['his.schedule_shift'].sudo()
        schedule_department_employee_obj = request.env['his.schedule_department_employee'].sudo()
        register_source_obj = request.env['his.register_source'].sudo()

        department_id = request.jsonrequest['data']['department_id']

        department = department_obj.search([('id', '=', department_id)])
        if not department:
            return {'state': 0, 'msg': '科室不存在'}

        today = (datetime.today() + timedelta(hours=8)).date()  # 当前日期
        result = []

        # 排班班次
        schedule_shifts = schedule_shift_obj.search([('department_id', '=', department_id),
                                                     ('schedule_id.date', '>=',
                                                      today.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                                                     ('schedule_id.date', '<=', (today + timedelta(
                                                         days=department.company_id.appoint_day)).strftime(
                                                         DEFAULT_SERVER_DATE_FORMAT))])

        # 排班班次按医生分组
        employee_group = {}
        for schedule_shift in schedule_shifts:
            employee_group.setdefault(schedule_shift.employee_id, []).append(schedule_shift)

        for employee in employee_group:
            schedule_department_employee = schedule_department_employee_obj.search([('department_id', '=', department_id), ('employee_id', '=', employee.id)])
            products = schedule_department_employee.product_ids
            fee = 0  # 总费用
            fee_name_group = {}  # 按收据费目分组
            for product in products:
                fee += product.list_price
                fee_name_group.setdefault(product.fee_name, 0)
                fee_name_group[product.fee_name] += product.list_price

            receipt_fee = [{'name': item[0], 'fee': item[1]} for item in fee_name_group.items()]  # 收据费目

            # 三天内的余号
            register_source_infos = []
            for i in range(3):
                date = (today + timedelta(days=i)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                register_sources = register_source_obj.search([('department_id', '=', department_id),
                                                               ('employee_id', '=', employee.id),
                                                               ('date', '=', date)])
                surplus_source = 0
                for register_source in register_sources:
                    if not register_source.readonly:
                        surplus_source += 1

                register_source_infos.append({
                    'date': date,
                    'surplus_source': surplus_source
                })

            result.append({
                'id': employee.id,  # 医生id
                'image': '/web/image/hr.employee/%s/image' % employee.id if employee.image else '',  # 头像,
                'name': employee.name,  # 姓名,
                'title': employee.title or '',  # 职务,
                'good_at': employee.good_at or '',  # 擅长,
                'introduction': employee.introduction or '',  # 简介,
                'write_date': datetime.strptime(employee.write_date, DEFAULT_SERVER_DATETIME_FORMAT).strftime('%Y%m%d%H%M%S'),  # 修改日期,
                'fee': fee,  # 总费用,
                'receipt_fee': receipt_fee,  # 收据费目
                'register_source_infos': register_source_infos,
                'allow_free': schedule_department_employee.allow_free, # 是否允许服务券支付
            })

        return {'state': 1, 'data': result}


    @http.route('/app/get_shift', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_shift(self):
        """获取班次"""

        def shift_is_full(schedule_shift1):
            """号是否已挂完"""
            is_full = True
            for register_source in schedule_shift1.register_source_ids:
                if register_source.readonly:  # 已过期
                    continue

                if register_source.state == '0':  # 待预约
                    is_full = False
                    break

            return is_full

        schedule_shift_obj = request.env['his.schedule_shift'].sudo()
        department_obj = request.env['hr.department'].sudo()

        department_id = request.jsonrequest['data']['department_id']
        employee_id = request.jsonrequest['data']['employee_id']

        department = department_obj.search([('id', '=', department_id)])
        if not department:
            return {'state': 0, 'msg': '科室不存在'}

        today = (datetime.today() + timedelta(hours=8)).date()  # 当前日期
        weeks = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']  # 星期

        # 排班班次
        schedule_shifts = schedule_shift_obj.search([('department_id', '=', department_id),
                                                     ('employee_id', '=', employee_id),
                                                     ('schedule_id.date', '>=',
                                                      today.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                                                     ('schedule_id.date', '<=', (today + timedelta(
                                                         days=department.company_id.appoint_day)).strftime(
                                                         DEFAULT_SERVER_DATE_FORMAT))])

        results = []

        for schedule_shift in schedule_shifts:
            if schedule_shift.expired:
                continue

            results.append({
                'id': schedule_shift.id,  # 班次Id
                'date': datetime.strptime(schedule_shift.schedule_id.date, DEFAULT_SERVER_DATE_FORMAT).strftime(
                    '%m-%d'),  # 日期
                'week': weeks[int(
                    datetime.strptime(schedule_shift.schedule_id.date, DEFAULT_SERVER_DATE_FORMAT).strftime('%w'))],
                # 星期名称
                'shift_name': schedule_shift.shift_type_id.name,  # 班次名称
                'is_stop': schedule_shift.is_stop,  # 是否停诊
                'is_full': shift_is_full(schedule_shift),  # 号是否已挂完
            })

        return {'state': 1, 'data': results}


    @http.route('/app/get_register_sources', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_register_sources(self):
        """10、返回医生号源"""
        data = request.jsonrequest['data']

        employee_id = data['employee_id']
        department_id = data['department_id']

        employee = request.env['hr.employee'].sudo().search([('id', '=', employee_id)])
        if not employee:
            return {'state': 0, 'msg': '医生不存在'}

        result = []
        # 查询该医生的排班

        today = (datetime.today() + timedelta(hours=8)).date()  # 当前日期
        schedule_shifts = request.env['his.schedule_shift'].sudo().search([('department_id', '=', department_id),
                                                                           ('schedule_id.employee_id', '=', employee.id),
                                                                           ('schedule_id.date', '>=', today.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                                                                           ('schedule_id.date', '<=', (today + timedelta(days=employee.company_id.appoint_day)).strftime(DEFAULT_SERVER_DATE_FORMAT))])
        for schedule_shift in schedule_shifts:
            if schedule_shift.is_stop: # 停诊
                continue

            register_sources = [
                {
                    'id': register_source.id,
                    'time_point_name': register_source.time_point_name,
                    'internal_id': register_source.internal_id,
                }for register_source in schedule_shift.register_source_ids if register_source.state == '0' and (not register_source.readonly)]


            result.append({
                'id': schedule_shift.id,
                'register_sources': register_sources
            })

        return {'state': 1, 'data': result}

    @http.route('/app/get_shift_register_sources', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_shift_register_sources(self):
        """返回班次号源"""
        register_source_obj = request.env['his.register_source'].sudo()

        data = request.jsonrequest['data']

        shift_id = data['shift_id']

        schedule_shift = request.env['his.schedule_shift'].sudo().search([('id', '=', shift_id)])

        if not schedule_shift:
            return {'state': 0, 'msg': '错误的班次'}

        # register_sources = [
        #     {
        #         'id': register_source.id,
        #         'time_point_name': register_source.time_point_name,
        #         'internal_id': register_source.internal_id,
        #     } for register_source in schedule_shift.register_source_ids if
        #     register_source.state == '0' and (not register_source.readonly)]

        if not schedule_shift.register_source_ids:
            return {'state': 1, 'data': []}

        register_sources = list(schedule_shift.register_source_ids)
        # 按时间点排序
        register_sources.sort(key=lambda a: a.time_point_name)
        # 查询第一条的顺序
        number = len(register_source_obj.search([('date', '=', schedule_shift.date),
                                                 ('department_id', '=', schedule_shift.department_id.id),
                                                 ('employee_id', '=', schedule_shift.employee_id.id),
                                                 ('time_point_name', '<', register_sources[0].time_point_name)]))
        res = []
        for register_source in register_sources:
            number += 1
            if register_source.state != '0' or register_source.readonly:
                continue
            # 计算当前号源的顺序

            res.append({
                'id': register_source.id,
                'time_point_name': register_source.time_point_name,
                'internal_id': register_source.internal_id,
                'number': number    # 号源顺序号
            })

        return {'state': 1, 'data': res}


    @http.route('/app/register_confirm_pay', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def register_confirm_pay(self):
        """挂号确认支付"""
        order_obj = request.env['sale.order'].sudo()
        register_source_obj = request.env['his.register_source'].sudo()
        department_employee_obj = request.env['his.schedule_department_employee'].sudo()
        reserve_record_obj = request.env['his.reserve_record'].sudo() # 预约记录
        partner_obj = request.env['res.partner'].sudo()
        long_pay_record_obj = request.env['his.long_pay_record'].sudo()

        data = request.jsonrequest['data']

        user_id = data['user_id'] # 当前支付用户的partner_id
        partner_id = data['partner_id'] # 就诊人ID
        register_source_id = data['register_source_id'] # 号源
        pay_method = data['pay_method'] # 支付方式
        # today = datetime.strptime(datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT), DEFAULT_SERVER_DATE_FORMAT) # 当前日期

        if not partner_obj.search([('id', '=', user_id)]):
            return {
                'state': 0,
                'msg': '当前用户不存在'
            }

        if not partner_obj.search([('id', '=', partner_id)]):
            return {
                'state': 0,
                'msg': '当前就诊人不存在'
            }

        # 查询号源对应产品
        register_source = register_source_obj.search([('id', '=', register_source_id)])
        if not register_source or register_source.state == '1': # 号源未锁定
            return {'state': 0, 'msg': '号源不可用'}

        # 挂号医院
        company = register_source.company_id

        department_employee = department_employee_obj.search([('department_id', '=', register_source.department_id.id), ('employee_id', '=', register_source.employee_id.id)])

        if not department_employee:
            return {'state': 0, 'msg': '预约失败'}

        reserve_record = reserve_record_obj.search([('partner_id', '=', partner_id),
                                   ('reserve_date', '=', register_source.date),
                                   ('department_id', '=', department_employee.department_id.id),
                                   ('employee_id', '=', department_employee.employee_id.id)], limit=1)

        if reserve_record:
            # order = reserve_record.order_id
            # if order.pay_method != 'free':
            #     if (order.alipay_ids or order.weixin_pay_ids) and not order.is_refund:
            #         return {'state': 0, 'msg': u'您已经预约%s%s%s' % (register_source.date, department_employee.department_id.name, department_employee.employee_id.name)}
            # else:
            if reserve_record.commit_his_state == '1': # 提交HIS成功
                return {'state': 0, 'msg': u'您已经预约%s%s%s' % (
                register_source.date, department_employee.department_id.name, department_employee.employee_id.name)}
            elif reserve_record.commit_his_state == '-1': # 未提交HIS

                if reserve_record.state not in ['draft', 'cancel']:
                    return {'state': 0, 'msg': u'您已经预约%s%s%s' % (register_source.date, department_employee.department_id.name, department_employee.employee_id.name)}

        # if datetime.strptime(register_source.date, DEFAULT_SERVER_DATE_FORMAT) > today:
        #     if reserve_records:
        #         return {'state': 0, 'msg': u'您已经预约%s%s%s' % (register_source.date, department_employee.department_id.name, department_employee.employee_id.name)}
        #
        # else:
        #     exist = False
        #     for reserve_record in reserve_records:
        #         if reserve_record.commit_his_state == '1' or (reserve_record.commit_his_state == '-1' and reserve_record.state == 'reserve'): # 已提交或(预约成功且未提交)
        #             exist = True
        #             break
        #
        #     if exist:
        #         return {'state': 0, 'msg': u'您已经预约%s%s%s' % (register_source.date, department_employee.department_id.name, department_employee.employee_id.name)}

        order_lines = None

        if pay_method not in ['free', 'coupon']:

            products = department_employee.product_ids

            # 创建订单草稿
            order_lines = [(0, 0, {
                'product_id': product.product_variant_id.id,
                'name': product.name,
                'product_uom_qty': 1,
                'price_unit': product.list_price,
                'product_uom': product.uom_id.id,
                'tax_id': False,
            })for product in products]

        order = order_obj.create({
            'partner_id': user_id,
            'visit_partner_id': partner_id,
            'order_line': order_lines,
            'company_id': company.id,
            'pay_method': pay_method,
            'order_type': 'register',
        })

        # 创建预约记录
        reserve_record = request.env['his.reserve_record'].sudo().create({
            'partner_id': partner_id,
            'reserve_date': register_source.date,
            'department_id': register_source.department_id.id,
            'employee_id': register_source.employee_id.id,
            'shift_type_id': register_source.shift_type_id.id,
            'register_source_id': register_source.id,
            'reserve_sort': False,
            'order_id': order.id,
            'register_id': False,
            'type': 'register',
            'state': 'draft',
            'company_id': company.id,
            'internal_id': False,
        })

        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        if base_url.endswith('/'):
            base_url = base_url[:-1]

        result = {
            'order_id': order.id,
            'pay_data': {},
        }

        if pay_method == 'weixin':
            # 获取医院的微信配置信息
            if not company.weixin_appid or not company.weixin_mch_id or not company.weixin_api_key:
                return {'state': 0, 'msg': u'%s暂不支持微信支付' % company.name}

            unifiedorder = UnifiedOrder_pub(appid=company.weixin_appid, mch_id=company.weixin_mch_id,
                                            api_key=company.weixin_api_key)

            unifiedorder.setParameter('body', '预约挂号') # 商品描述
            unifiedorder.setParameter('out_trade_no', order.name) # 商记订单号
            unifiedorder.setParameter('total_fee', str(int(round(order.amount_total, 2) * 100))) # 总金额
            unifiedorder.setParameter('spbill_create_ip', '127.0.0.1') # TODO 终端IP
            unifiedorder.setParameter('notify_url', '%s/app/weixin_payback' % base_url) # 通知地址
            unifiedorder.setParameter('trade_type', 'APP')
            unifiedorder.setParameter('attach', order.name)

            response = xmltodict.parse(unifiedorder.postXmlSSL())

            _logger.info('挂号微信预支付响应信息：%s' % response)
            if not response['xml'].get('prepay_id'):
                return {'state': 0, 'msg': '下单错误!'}

            # 生成支付随机字符串
            nonce = unifiedorder.createNoncestr()

            # 时间戳
            timestamp = str(int(time.time()))

            # 支付参数
            parameter = {
                'partnerid': response['xml']['mch_id'],
                'appid':response['xml']['appid'],
                'prepayid': response['xml']['prepay_id'],
                'package': 'Sign=WXPay',
                'noncestr': nonce,
                'timestamp': timestamp,
            }
            # 签名
            sign = unifiedorder.getSign(parameter)

            result['pay_data'].update({
                'mch_id': response['xml']['mch_id'],  # 商户号
                'appid': response['xml']['appid'],  # 应用ID
                'prepay_id': response['xml']['prepay_id'],  # 预支付交易会话标识
                'package': 'Sign=WXPay',
                'nonce': nonce,  # 随机字符
                'timestamp': timestamp,
                'signparams': sign,  # 签名
            })
        elif pay_method == 'alipay':
            if not company.alipay_app_id or not company.app_alipay_private_key or not company.app_alipay_public_key:
                return {'state': 0, 'msg': u'%s暂不支持支付宝支付' % company.name}

            ali = AliPay(appid=company.alipay_app_id,
                         app_private_key_path=company.app_alipay_private_key_path,
                         app_alipay_public_key_path=company.app_alipay_public_key_path,
                         sign_type='RSA2',
                         app_notify_url=base_url+'/app/alipay_payback')

            order_string = ali.create_app_trade(out_trade_no=order.name, total_amount=order.amount_total, subject="预约挂号", passback_params=order.name)

            result['pay_data'].update({
                'order_info': order_string
            })
        elif pay_method == 'longpay':
            # 建行龙支付
            if not company.long_mch_id or not company.long_counter_id or not company.long_branch_code or not company.long_mch_phone or not company.long_key:
                return {'state': 0, 'msg': u'%s暂不支持龙支付' % company.name}

            parameter = long_pay_record_obj.get_pay_parameter(company, [order])
            result['pay_data'].update({
                'parameter': parameter
            })

        elif order.pay_method in ['free', 'coupon']:
            # 订单确认
            order.action_confirm()
            partner = order.visit_partner_id  # 订单关联的就诊人
            patient = request.env['hrp.patient'].sudo().search([('partner_id', '=', partner.id), ('company_id', '=', order.company_id.id)], limit=1)  # 就诊人
            # 修改预约记录
            reserve_record.state = 'reserve'
            # 发送内网消息
            msg = {
                'action': 'register_done',
                'data': {
                    'partner_id': patient.internal_id,  # 患者内部id
                    'appointment_record': {
                        'id': reserve_record.id,  # 记录id
                        'department_id': reserve_record.department_id.internal_id,  # 科室id
                        'employee_id': reserve_record.employee_id.internal_id,  # 医生id
                        'shift_id': reserve_record.shift_type_id.internal_id,  # 班次id
                        'register_source_id': reserve_record.register_source_id.internal_id,  # 号源id
                        'date': reserve_record.reserve_date  # 预约日期
                    },
                    'pay_method': order.pay_method,
                    'pay_result': None,
                }
            }
            Emqtt.publish(order.company_id.topic, msg)

        return {'state': 1, 'data': result}


    @http.route('/app/payment_confirm_pay', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def payment_confirm_pay(self):
        """缴费确认支付"""
        order_obj = request.env['sale.order'].sudo()
        product_obj = request.env['product.template'].sudo()
        company_obj = request.env['res.company'].sudo()
        long_pay_record_obj = request.env['his.long_pay_record'].sudo()

        data = request.jsonrequest['data']

        user_id = data['user_id'] # 当前支付用户的partner_id
        partner_id = data['partner_id'] # 就诊人ID
        company_id = data['company_id'] # 医院ID
        pay_method = data['pay_method'] # 支付方式

        # 创建订单
        orders = []
        for payment in data['payment_list']:    # 选择的确缴费清单
            order_line = []
            for detail in payment['details']:
                product = product_obj.search([('company_id', '=', company_id), ('internal_id', '=', detail['product_id'])])
                order_line.append((0, 0, {
                    'product_id': product.product_variant_id.id,
                    'name': detail['name'],
                    'product_uom_qty': detail['qty'],
                    'price_unit': detail['price'],
                    'product_uom': product.uom_id.id,
                    'fee_name': detail['fee_name'], # 收据费目
                    'tax_id': False,
                }))
            order = order_obj.create({
                'partner_id': user_id, # 当前支付用户的partner_id,
                'visit_partner_id': partner_id, # 就诊人ID,
                'company_id': company_id, # 医院ID,
                'pay_method': pay_method, # 支付方式,
                'order_type': 'payment',
                'receipt_no': payment['receipt_no'], # 单据号
                'order_line': order_line,
            })
            orders.append(order)

        if not orders:
            return {'state': 0, 'msg': '创建订单错误!'}

        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        if base_url.endswith('/'):
            base_url = base_url[:-1]

        result = {
            'order_ids': [order.id for order in orders],
            'pay_data': {}
        }

        out_trade_no = orders[0].name # 商户订单号
        amount_total = round(sum([order.amount_total for order in orders]), 2) # 订单总额
        attach = '|'.join([order.name for order in orders]) # 附加数据包

        company = company_obj.search([('id', '=', company_id)])
        if not company:
            return {'state': 0, 'msg': '选择的医院错误'}

        if pay_method == 'weixin':
            # 获取医院的微信配置信息
            if not company.weixin_appid or not company.weixin_mch_id or not company.weixin_api_key:
                return {'state': 0, 'msg': '该医院暂不支持微信支付'}

            unifiedorder = UnifiedOrder_pub(appid=company.weixin_appid, mch_id=company.weixin_mch_id,
                                            api_key=company.weixin_api_key)

            unifiedorder.setParameter('body', '缴费') # 商品描述
            unifiedorder.setParameter('out_trade_no', out_trade_no) # 商记订单号
            unifiedorder.setParameter('total_fee', str(int(amount_total * 100))) # 总金额
            unifiedorder.setParameter('spbill_create_ip', '127.0.0.1') # TODO 终端IP
            unifiedorder.setParameter('notify_url', '%s/app/weixin_payback' % base_url) # 通知地址
            unifiedorder.setParameter('trade_type', 'APP')
            unifiedorder.setParameter('attach', attach)

            response = xmltodict.parse(unifiedorder.postXmlSSL())

            _logger.info('缴费微信预支付响应信息：%s' % response)
            if not response['xml'].get('prepay_id'):
                return {'state': 0, 'msg': '下单错误!'}

            # 生成支付随机字符串
            nonce = unifiedorder.createNoncestr()

            # 时间戳
            timestamp = str(int(time.time()))

            # 支付参数
            parameter = {
                'partnerid': response['xml']['mch_id'],
                'appid': response['xml']['appid'],
                'prepayid': response['xml']['prepay_id'],
                'package': 'Sign=WXPay',
                'noncestr': nonce,
                'timestamp': timestamp,
            }
            # 签名
            sign = unifiedorder.getSign(parameter)

            result['pay_data'].update({
                'mch_id': response['xml']['mch_id'],  # 商户号
                'appid': response['xml']['appid'],  # 应用ID
                'prepay_id': response['xml']['prepay_id'],  # 预支付交易会话标识
                'package': 'Sign=WXPay',
                'nonce': nonce,  # 随机字符
                'timestamp': timestamp,
                'signparams': sign,  # 签名
            })

        elif pay_method == 'alipay':
            # 获取医院的支付宝配置信息
            if not company.alipay_app_id or not company.app_alipay_private_key or not company.app_alipay_public_key:
                return {'state': 0, 'msg': '该医院暂不支持支付宝支付'}

            ali = AliPay(appid=company.alipay_app_id,
                         app_private_key_path=company.app_alipay_private_key_path,
                         app_alipay_public_key_path=company.app_alipay_public_key_path,
                         sign_type='RSA2',
                         app_notify_url=base_url + '/app/alipay_payback')

            order_string = ali.create_app_trade(out_trade_no=out_trade_no, total_amount=amount_total, subject="缴费",
                                                passback_params=attach)

            result['pay_data'].update({
                'order_info': order_string
            })
        elif pay_method == 'longpay':
            # 建行龙支付
            if not company.long_mch_id or not company.long_counter_id or not company.long_branch_code or not company.long_mch_phone or not company.long_key:
                return {'state': 0, 'msg': u'%s暂不支持龙支付' % company.name}

            parameter = long_pay_record_obj.get_pay_parameter(company, orders)
            result['pay_data'].update({
                'parameter': parameter
            })

        return {'state': 1, 'data': result}


    @http.route('/app/recharge_confirm_pay', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def recharge_confirm_pay(self):
        """确认充值"""
        order_obj = request.env['sale.order'].sudo()
        product_obj = request.env['product.template'].sudo()
        product_category_obj = request.env['product.category'].sudo()
        company_obj = request.env['res.company'].sudo()
        long_pay_record_obj = request.env['his.long_pay_record'].sudo()

        data = request.jsonrequest['data']

        user_id = data['user_id'] # 当前支付用户的partner_id
        partner_id = data['partner_id'] # 就诊人ID
        company_id = data['company_id'] # 医院ID
        pay_method = data['pay_method'] # 支付方式
        amount = round(data['amount'], 2)  # 充值金额
        recharge_type = data['recharge_type']  # 充值类型

        if amount < 0.01:
            return {'state': 0, 'msg': '请输入正确的充值金额'}

        if amount > 99999.99:
            return {'state': 0, 'msg': '充值金额不能大于99999.99'}

        # 创建订单
        product_category = product_category_obj.search([('name', '=', u'充值'), ('company_id', '=', company_id)])
        product = product_obj.search([('categ_id', '=', product_category.id)], limit=1)

        if not product:
            return {'state': 0, 'msg': '没有充值产品'}

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
            'partner_id': user_id,  # 当前支付用户的partner_id,
            'visit_partner_id': partner_id,  # 就诊人ID,
            'company_id': company_id,  # 医院ID,
            'pay_method': pay_method,  # 支付方式,
            'order_type': 'recharge', # 充值
            # 'receipt_no': payment['receipt_no'],  # 单据号
            'order_line': order_line,
            'recharge_type': recharge_type, # 充值类型
        })
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        if base_url.endswith('/'):
            base_url = base_url[:-1]

        result = {
            'order_ids': [order.id],
            'pay_data': {}
        }

        out_trade_no = order.name # 商户订单号
        amount_total = amount # 订单总额
        attach = '|'.join([order.name]) # 附加数据包

        company = company_obj.search([('id', '=', company_id)])
        if not company:
            return {'state': 0, 'msg': '选择的医院错误'}

        if pay_method == 'weixin':
            # 获取医院的微信配置信息
            if not company.weixin_appid or not company.weixin_mch_id or not company.weixin_api_key:
                return {'state': 0, 'msg': '该医院暂不支持微信支付'}

            unifiedorder = UnifiedOrder_pub(appid=company.weixin_appid, mch_id=company.weixin_mch_id, api_key=company.weixin_api_key)

            unifiedorder.setParameter('body', '充值') # 商品描述
            unifiedorder.setParameter('out_trade_no', out_trade_no) # 商记订单号
            unifiedorder.setParameter('total_fee', str(int(amount_total * 100))) # 总金额
            unifiedorder.setParameter('spbill_create_ip', '127.0.0.1') # TODO 终端IP
            unifiedorder.setParameter('notify_url', '%s/app/weixin_payback' % base_url) # 通知地址
            unifiedorder.setParameter('trade_type', 'APP')
            unifiedorder.setParameter('attach', attach)

            response = xmltodict.parse(unifiedorder.postXmlSSL())

            _logger.info('充值微信预支付响应信息：%s' % response)
            if not response['xml'].get('prepay_id'):
                return {'state': 0, 'msg': '下单错误!'}

            # 生成支付随机字符串
            nonce = unifiedorder.createNoncestr()

            # 时间戳
            timestamp = str(int(time.time()))

            # 支付参数
            parameter = {
                'partnerid': response['xml']['mch_id'],
                'appid': response['xml']['appid'],
                'prepayid': response['xml']['prepay_id'],
                'package': 'Sign=WXPay',
                'noncestr': nonce,
                'timestamp': timestamp,
            }
            # 签名
            sign = unifiedorder.getSign(parameter)

            result['pay_data'].update({
                'mch_id': response['xml']['mch_id'],  # 商户号
                'appid': response['xml']['appid'],  # 应用ID
                'prepay_id': response['xml']['prepay_id'],  # 预支付交易会话标识
                'package': 'Sign=WXPay',
                'nonce': nonce,  # 随机字符
                'timestamp': timestamp,
                'signparams': sign,  # 签名
            })

        elif pay_method == 'alipay':
            # 获取医院的支付宝配置信息
            if not company.alipay_app_id or not company.app_alipay_private_key or not company.app_alipay_public_key:
                return {'state': 0, 'msg': '该医院暂不支持支付宝支付'}

            ali = AliPay(appid=company.alipay_app_id,
                         app_private_key_path=company.app_alipay_private_key_path,
                         app_alipay_public_key_path=company.app_alipay_public_key_path,
                         sign_type='RSA2',
                         app_notify_url=base_url + '/app/alipay_payback')

            order_string = ali.create_app_trade(out_trade_no=out_trade_no, total_amount=amount_total, subject="充值",
                                                passback_params=attach)

            result['pay_data'].update({
                'order_info': order_string
            })
        elif pay_method == 'longpay':
            # 建行龙支付
            if not company.long_mch_id or not company.long_counter_id or not company.long_branch_code or not company.long_mch_phone or not company.long_key:
                return {'state': 0, 'msg': u'%s暂不支持龙支付' % company.name}

            parameter = long_pay_record_obj.get_pay_parameter(company, [order])
            result['pay_data'].update({
                'parameter': parameter
            })

        return {'state': 1, 'data': result}


    @http.route('/app/weixin_payback', type='http', auth="public", methods=['POST'], cors='*', csrf=False)
    def weixin_payback(self):
        """微信支付成功回调"""
        order_obj = request.env['sale.order'].sudo()
        weixin_pay_record_obj = request.env['his.weixin_pay_record'].sudo()
        company_obj = request.env['res.company'].sudo()

        _logger.info(u'微信支付通知收到数据:%s', request.httprequest.data)

        result = xmltodict.unparse({'xml': {'return_code': 'SUCCESS', 'return_msg': 'OK'}},
                                   full_document=False)  # 返回的信息

        response_data = xmltodict.parse(request.httprequest.data)

        # 获取对应医院
        company = company_obj.search([('weixin_appid', '=', response_data['xml']['appid'])], limit=1)

        if not company:
            _logger.error(u'此appid未找到对应医院')
            return result

        if not company.weixin_appid or not company.weixin_mch_id or not company.weixin_api_key:
            _logger.error(u'%s医院微信信息不全' % company.name)
            return result

        # 响应类
        wxpay_server_pub = Wxpay_server_pub(appid=company.weixin_appid, mch_id=company.weixin_mch_id, api_key=company.weixin_api_key)
        wxpay_server_pub.saveData(request.httprequest.data)

        # 验证签名
        if not wxpay_server_pub.checkSign():
            _logger.error(u'微信支付通知验证签名失败')
            return

        notify_data = wxpay_server_pub.data

        if notify_data['return_code'] == 'FAIL': # 返回状态码
            _logger.error(u'支付失败')
            return result

        out_trade_no = notify_data['out_trade_no'] # 商户订单号
        order = order_obj.search([('name', '=', out_trade_no)])
        if not order:
            _logger.error(u'微信支付通知订单不存在')
            return result

        # 避免重复处理
        transaction_id = notify_data['transaction_id']  # 微信支付订单号
        if weixin_pay_record_obj.search([('transaction_id', '=', transaction_id)]):
            _logger.error(u'微信支付订单号重复')
            return result

        attach = notify_data['attach']  # 商家数据包
        order_names = attach.split('|')
        orders = order_obj.search([('name', 'in', order_names)])

        # 验证金额
        amount_total = sum([o.amount_total for o in orders])
        if amount_total != int(notify_data['cash_fee']) / 100.0:
            _logger.error(u'微信支付通知金额与订单金额不符')
            return result

        # 创建支付记录
        weixin_pay_record_obj.create({
            'return_code': notify_data.get('return_code'), # 返回状态码
            'return_msg': notify_data.get('return_msg'), # 返回信息
            'appid': notify_data.get('appid'), # 应用ID
            'mch_id': notify_data.get('mch_id'), # 商户号
            'device_info': notify_data.get('device_info'), # 设备号
            'nonce_str': notify_data.get('nonce_str'), # 随机字符串
            'sign': notify_data.get('sign'), # 签名
            'result_code': notify_data.get('result_code'), # 业务结果
            'err_code': notify_data.get('err_code'), # 错误代码
            'err_code_des': notify_data.get('err_code_des'), # 错误代码描述
            'openid': notify_data.get('openid'), # 用户标识
            'is_subscribe': notify_data.get('is_subscribe'), # 是否关注公众账号
            'trade_type': notify_data.get('trade_type'), # 交易类型
            'bank_type': notify_data.get('bank_type'), # 付款银行
            'total_fee': notify_data.get('total_fee'), # 总金额
            'fee_type': notify_data.get('fee_type'), # 货币种类
            'cash_fee': notify_data.get('cash_fee'), # 现金支付金额
            'cash_fee_type': notify_data.get('cash_fee_type'), # 现金支付货币类型
            'transaction_id': notify_data.get('transaction_id'), # 微信支付订单号
            'out_trade_no': notify_data.get('out_trade_no'), # 商户订单号
            'attach': notify_data.get('attach'), # 商家数据包
            'time_end': notify_data.get('time_end'), # 支付完成时间
            'order_ids': [(6, 0, [o.id for o in orders])],
            'company_id': order.company_id.id,
        })

        if notify_data['result_code'] == 'FAIL':# 业务结果
            return result

        # 订单确认
        orders.action_confirm()
        partner = order.visit_partner_id  # 订单关联的就诊人
        patient = request.env['hrp.patient'].sudo().search([('partner_id', '=', partner.id), ('company_id', '=', order.company_id.id)], limit=1)  # 就诊人

        # 挂号处理
        if order.order_type == 'register':
            # 修改预约记录状态
            reserve_record = request.env['his.reserve_record'].sudo().search([('order_id', '=', order.id)])
            reserve_record.state = 'reserve'

            # 发送内网消息
            msg = {
                'action': 'register_done',
                'data': {
                    'partner_id': patient.internal_id,  # 患者内部id
                    'appointment_record': {
                        'id': reserve_record.id, # 记录id
                        'department_id': reserve_record.department_id.internal_id, # 科室id
                        'employee_id': reserve_record.employee_id.internal_id, # 医生id
                        'shift_id': reserve_record.shift_type_id.internal_id, # 班次id
                        'register_source_id': reserve_record.register_source_id.internal_id, # 号源id
                        'date': reserve_record.reserve_date # 预约日期
                    },
                    'pay_method': order.pay_method,
                    'pay_result': notify_data,
                }
            }
            Emqtt.publish(order.company_id.topic, msg)

        # 缴费处理
        if order.order_type == 'payment':
            # 发送内网消息
            msg = {
                'action': 'payment_done',
                'data': {
                    'partner_id': patient.internal_id,  # 患者内部id
                    'order_info': [
                        {
                            'id': order.id, # 订单外网id
                            'receipt_no': order.receipt_no, # 单据号
                            'details': [
                                {
                                    'product_id': line.product_id.product_tmpl_id.internal_id, # 收费项目内部ID
                                    'name': line.name, # 产品名称
                                    'price': line.price_unit, # 单价
                                    'qty': line.product_uom_qty, # 数量
                                    'fee_name': line.fee_name
                                } for line in order.order_line] # 缴费明细
                        } for order in orders],
                    'pay_method': order.pay_method,
                    'pay_result': notify_data,
                }
            }
            Emqtt.publish(order.company_id.topic, msg)

        # 充值
        if order.order_type == 'recharge':
            # 发送内网消息
            msg = {
                'action': 'recharge_done',
                'data': {
                    'partner_id': patient.internal_id,  # 患者内部id
                    'order_id': order.id, # 订单外网id,
                    'pay_method': order.pay_method,
                    'pay_result': notify_data,
                    'amount': order.amount_total, # 充值金额
                    'recharge_type': order.recharge_type, # 充值类型
                }
            }
            Emqtt.publish(order.company_id.topic, msg)


        # 便民服务
        if order.order_type == 'service':
            # 发送内网消息
            msg = {
                'action': 'service_pay_done',
                'data': {
                    'partner_id': patient.internal_id,  # 患者内部id
                    'order_id': order.id, # 订单外网id,
                    'pay_method': order.pay_method,
                    'pay_result': notify_data,
                    'convenient_item_id': order.convenient_item_id.internal_id, # 便民服务项目ID
                }
            }
            Emqtt.publish(order.company_id.topic, msg)

        return result

    @http.route('/app/alipay_payback', type='http', auth="public", methods=['POST'], cors='*', csrf=False)
    def alipay_payback(self, **kwargs):
        """支付宝支付成功回调"""
        order_obj = request.env['sale.order'].sudo()
        alipay_record_obj = request.env['his.alipay_record'].sudo()
        company_obj = request.env['res.company'].sudo()

        _logger.info(u'支付宝支付通知收到数据kwargs:%s', kwargs)

        result = xmltodict.unparse({'xml': {'return_code': 'SUCCESS', 'return_msg': 'OK'}},
                                   full_document=False)  # 返回的信息

        # 获取对应医院
        company = company_obj.search([('alipay_app_id', '=', kwargs['app_id'])], limit=1)
        if not company:
            _logger.error(u'此appid未找到对应医院')
            return result

        if not company.alipay_app_id or not company.app_alipay_private_key or not company.app_alipay_public_key:
            _logger.error(u'%s医院支付宝配置信息不全' % company.name)
            return result

        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        if base_url.endswith('/'):
            base_url = base_url[:-1]

        ali = AliPay(appid=company.alipay_app_id,
                     app_private_key_path=company.app_alipay_private_key_path,
                     app_alipay_public_key_path=company.app_alipay_public_key_path,
                     sign_type='RSA2',
                     app_notify_url=base_url + '/app/alipay_payback')

        notify_data = kwargs.copy()

        # 验证签名
        sign = kwargs.pop('sign')

        if not ali.verify_app_notify(kwargs, sign):
            _logger.error(u'验证支付宝服务器通知失败')
            return result

        # 避免重复处理
        if alipay_record_obj.search([('notify_id', '=', kwargs.get('notify_id'))]):
            _logger.error(u'支付宝通知重复')
            return result
        # 查询订单
        order = order_obj.search([('name', '=', kwargs.get('out_trade_no'))])
        if not order:
            _logger.error(u'支付宝支付订单不存在')
            return result

        passback_params = kwargs['passback_params']  # 商家数据包
        order_names = passback_params.split('|')
        orders = order_obj.search([('name', 'in', order_names)])

        # 验证金额
        amount_total = sum([o.amount_total for o in orders])
        if amount_total != float(kwargs['total_amount']):
            _logger.error(u'支付宝支付金额与订单金额不符')
            return result

        # 创建支付宝支付记录
        alipay_record = alipay_record_obj.create({
            'notify_time': kwargs.get('notify_time'),
            'notify_type': kwargs.get('notify_type'),
            'notify_id': kwargs.get('notify_id'),
            'app_id': kwargs.get('app_id'),
            'charset': kwargs.get('charset'),
            'version': kwargs.get('version'),
            'sign_type': kwargs.get('sign_type'),
            'sign': sign,
            'out_trade_no': kwargs.get('out_trade_no'),
            'trade_no': kwargs.get('trade_no'),
            'trade_status': kwargs.get('trade_status'),
            'total_amount': kwargs.get('total_amount'),
            'receipt_amount': kwargs.get('receipt_amount'),
            'buyer_pay_amount': kwargs.get('buyer_pay_amount'),
            'gmt_create': kwargs.get('gmt_create'),
            'gmt_payment': kwargs.get('gmt_payment'),
            'gmt_close': kwargs.get('gmt_close'),
            'passback_params': kwargs.get('passback_params'),
            'order_ids': [(6, 0, [o.id for o in orders])],
            'company_id': order.company_id.id,
        })
        # 结果状态
        if alipay_record.trade_status not in ['TRADE_SUCCESS', 'TRADE_FINISHED']:
            _logger.error(u'支付失败')
            return result

        # 订单确认
        orders.action_confirm()
        partner = order.visit_partner_id  # 订单关联的就诊人
        patient = request.env['hrp.patient'].sudo().search([('partner_id', '=', partner.id), ('company_id', '=', order.company_id.id)], limit=1)  # 就诊人

        # 挂号处理
        if order.order_type == 'register':
            # 修改预约记录状态
            reserve_record = request.env['his.reserve_record'].sudo().search([('order_id', '=', order.id)])
            reserve_record.state = 'reserve'

            # 发送内网消息
            msg = {
                'action': 'register_done',
                'data': {
                    'partner_id': patient.internal_id,  # 患者内部id
                    'appointment_record': {
                        'id': reserve_record.id,  # 记录id
                        'department_id': reserve_record.department_id.internal_id,  # 科室id
                        'employee_id': reserve_record.employee_id.internal_id,  # 医生id
                        'shift_id': reserve_record.shift_type_id.internal_id,  # 班次id
                        'register_source_id': reserve_record.register_source_id.internal_id,  # 号源id
                        'date': reserve_record.reserve_date  # 预约日期
                    },
                    'pay_method': order.pay_method,
                    'pay_result': notify_data,
                }
            }
            Emqtt.publish(order.company_id.topic, msg)

        # 缴费处理
        if order.order_type == 'payment':
            # 发送内网消息
            msg = {
                'action': 'payment_done',
                'data': {
                    'partner_id': patient.internal_id,  # 患者内部id
                    'order_info': [
                        {
                            'id': order.id,  # 订单外网id
                            'receipt_no': order.receipt_no,  # 单据号
                            'details': [
                                {
                                    'product_id': line.product_id.product_tmpl_id.internal_id,  # 收费项目内部ID
                                    'name': line.name,  # 产品名称
                                    'price': line.price_unit,  # 单价
                                    'qty': line.product_uom_qty,  # 数量
                                    'fee_name': line.fee_name
                                } for line in order.order_line]  # 缴费明细
                        } for order in orders],
                    'pay_method': order.pay_method,
                    'pay_result': notify_data,
                }
            }
            Emqtt.publish(order.company_id.topic, msg)

        # 充值
        if order.order_type == 'recharge':
            # 发送内网消息
            msg = {
                'action': 'recharge_done',
                'data': {
                    'partner_id': patient.internal_id,  # 患者内部id
                    'order_id': order.id, # 订单外网id,
                    'pay_method': order.pay_method,
                    'pay_result': notify_data,
                    'amount': order.amount_total,  # 充值金额
                    'recharge_type': order.recharge_type,  # 充值类型
                }
            }
            Emqtt.publish(order.company_id.topic, msg)


        # 便民服务
        if order.order_type == 'service':
            # 发送内网消息
            msg = {
                'action': 'service_pay_done',
                'data': {
                    'partner_id': patient.internal_id,  # 患者内部id
                    'order_id': order.id, # 订单外网id,
                    'pay_method': order.pay_method,
                    'pay_result': notify_data,
                    'convenient_item_id': order.convenient_item_id.internal_id, # 便民服务项目ID
                }
            }
            Emqtt.publish(order.company_id.topic, msg)

        return result

    @http.route('/app/long_payback', type='http', auth="public", methods=['GET'], cors='*', csrf=False)
    def long_payback(self, **kwargs):
        """支付宝支付成功回调"""
        order_obj = request.env['sale.order'].sudo()
        company_obj = request.env['res.company'].sudo()

        _logger.info(u'龙支付通知收到数据kwargs:%s', kwargs)
        _logger.info(u'龙支付通知收到数据request.httprequest.data:%s', request.httprequest.data)

        result = xmltodict.unparse({'xml': {'return_code': 'SUCCESS', 'return_msg': 'OK'}},
                                   full_document=False)  # 返回的信息

        return result

    @http.route('/app/get_order_pay_state', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_order_pay_state(self):
        """支付结果状态"""
        order_id = request.jsonrequest['data']['order_id']

        order = request.env['sale.order'].sudo().search([('id', '=', order_id)])

        if not order:
            return {'state': 0, 'msg': '订单不存在'}

        if order.pay_method not in ['free', 'coupon']:
            if not order.weixin_pay_ids and not order.alipay_ids:
                return {
                    'state': 1,
                    'data': {
                        'pay_state': -1
                    }
                }

        amount = 0  # 支付金额
        # 微信支付失败
        if order.pay_method == 'weixin':
            weixin_pay = order.weixin_pay_ids[0]
            if weixin_pay.result_code == 'FAIL':
                return {
                    'state': 1,
                    'data': {
                        'pay_state': 0
                    },
                }

            amount = weixin_pay.cash_fee / 100.0

        elif order.pay_method == 'alipay':
            alipay = order.alipay_ids[0]
            if alipay.trade_status not in ['TRADE_FINISHED', 'TRADE_SUCCESS']:  # TRADE_FINISHED-交易结束，不可退款 TRADE_SUCCESS-交易支付成功
                return {
                    'state': 1,
                    'data': {
                        'pay_state': 0
                    }
                }
            amount = alipay.buyer_pay_amount

        res = {
            'pay_state': 1,
            'business_state': -1,
            'amount': amount,
            'business_result': {}
        }

        # 挂号
        if order.order_type == 'register':
            reserve_record = request.env['his.reserve_record'].sudo().search([('order_id', '=', order.id)])
            if reserve_record.reserve_sort:  # 内网返回预约号
                res.update({
                    'business_state': 1,
                    'business_result': {
                        'location': reserve_record.department_id.location or '',
                        'reserve_sort': reserve_record.reserve_sort,
                    }
                })

            return {'state': 1, 'data': res}

        # 缴费
        if order.order_type == 'payment':
            if order.commit_his_state == '-1':
                res.update({
                    'business_state': -1,
                    'business_result': {}
                })

            if order.commit_his_state == '0':
                res.update({
                    'business_state': 0,
                    'business_result': {
                        'msg': order.commit_his_error_msg
                    }
                })

            if order.commit_his_state == '1':
                res.update({
                    'business_state': 1,
                    'business_result': {}
                })

            return {'state': 1, 'data': res}


        # 充值
        if order.order_type == 'recharge':
            if order.commit_his_state == '-1':
                res.update({
                    'business_state': -1,
                    'business_result': {}
                })

            if order.commit_his_state == '0':
                res.update({
                    'business_state': 0,
                    'business_result': {
                        'msg': order.commit_his_error_msg
                    }
                })

            if order.commit_his_state == '1':
                res.update({
                    'business_state': 1,
                    'business_result': {
                        'mz_balance': order.mz_balance,
                        'zy_balance': order.zy_balance,
                    }
                })

            return {'state': 1, 'data': res}

        # 划价收费
        if order.order_type == 'service':
            if order.commit_his_state == '-1':
                res.update({
                    'business_state': -1,
                    'business_result': {}
                })

            if order.commit_his_state == '0':
                res.update({
                    'business_state': 0,
                    'business_result': {
                        'msg': order.commit_his_error_msg
                    }
                })

            if order.commit_his_state == '1':
                res.update({
                    'business_state': 1,
                })

            return {'state': 1, 'data': res}


        return {
            'state': 1,
            'data': {
                'pay_state': 1,
                'business_state': 1,
                'amount': amount,
                'business_result': {

                }
            }
        }


    @http.route('/app/get_reserve_record', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_reserve_record(self):
        """查询预约记录"""
        def get_state():
            state = reserve_record.state # 预约记录状态
            commit_his_state = reserve_record.commit_his_state # 提交HIS状态
            if commit_his_state == '-1': # 未提交
                if state == 'reserve':
                    return '成功'
                return '取消'
            elif commit_his_state == '0':
                return '失败'
            else:
                return '成功'

        def get_can_cancel():
            state = reserve_record.state # 预约记录状态
            commit_his_state = reserve_record.commit_his_state # 提交HIS状态
            if commit_his_state == '1': # 提交成功
                return 0

            if state == 'reserve':
                return 1

            return 0

        reserve_record_obj = request.env['his.reserve_record'].sudo() # 预约记录
        partner_obj = request.env['res.partner'].sudo()

        data = request.jsonrequest['data']
        partner_id = data['partner_id'] # 当前用户对应的partner_id
        company_id = data['company_id'] # 当前医院ID

        partner = partner_obj.browse(partner_id) # 当前
        patient_ids = [relationship.partner_id.id for relationship in partner.relationship_ids] # 当前用户关联的就诊人
        patient_ids += [partner_id]

        reserve_date = (datetime.now() - timedelta(days=30)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        reserve_records = reserve_record_obj.search([
            ('company_id', '=', company_id),
            ('reserve_date', '>=', reserve_date),
            ('partner_id', 'in', patient_ids),
            ('type', '=', 'register'),
            ('state', '!=', 'draft')])

        if not reserve_records:
            return {
                'state': 0,
                'msg': '没有预约挂号'
            }

        return {
            'state': 1,
            'data': [
            {
                'reserve_id': reserve_record.id, # 预约记录ID
                'partner_name': reserve_record.partner_id.name, # 就诊人
                'reserve_date': reserve_record.reserve_date, # 预约日期
                'department': reserve_record.department_id.name, # 预约科室
                'employee': reserve_record.employee_id.name,  # 预约医生
                'time_point_name': reserve_record.register_source_id.time_point_name, # 预约时间点
                'state': get_state(), # 记录状态
                'reserve_sort': reserve_record.reserve_sort,  # 预约顺序号
                'get_can_cancel': get_can_cancel(), # 是否可取消

            }for reserve_record in reserve_records],
        }

    @http.route('/app/cancel_reserve_record', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def cancel_reserve_record(self):
        """取消预约挂号"""
        reserve_record_obj = request.env['his.reserve_record'].sudo() # 预约记录
        refund_apply_obj = request.env['his.refund_apply'].sudo() # 退款申请
        partner_obj = request.env['res.partner'].sudo()

        data = request.jsonrequest['data']
        partner_id = data['partner_id'] # 当前用户对应的partner_id
        reserve_id = data['reserve_id'] # 预约记录ID

        partner = partner_obj.browse(partner_id)

        patient_ids = [relationship.partner_id.id for relationship in partner.relationship_ids] # 当前用户关联的就诊人
        patient_ids += [partner_id]

        reserve_record = reserve_record_obj.browse(reserve_id)

        if reserve_record.partner_id.id not in patient_ids:
            return {
                'state': 0,
                'msg': '预约记录不存在'
            }

        if reserve_record.state == 'commit':
            return {
                'state': 0,
                'msg': '预约记录已提交HIS,请到人工挂号窗口退号'
            }

        if reserve_record.state in ['done', 'cancel', 'draft']:
            return {
                'state': 0,
                'msg': '预约记录已经就诊或已被取消'
            }

        # 当天不能取消
        today = (datetime.now() + timedelta(hours=8)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        if reserve_record.reserve_date == today:
            return {
                'state': 0,
                'msg': '当天的预约挂号请到人工窗口取消'
            }

        # 取消订单
        order = reserve_record.order_id
        order.action_cancel()
        # 更新预约记录
        reserve_record.write({
            'state': 'cancel',
            'cancel_type': '1', # 用户取消
        })
        refund_apply_id = False
        if order.pay_method not in ['free', 'coupon']:
            # 创建退款申请
            res = {
                'partner_id': partner_id,
                'visit_partner_id': reserve_record.partner_id.id,
                'pay_method': order.pay_method,
                'amount_total': order.amount_total,
                'order_ids': [(6, 0, [order.id])],
                'state': 'draft',
                'company_id': reserve_record.company_id.id,
                'reason': '取消预约挂号',
            }
            if order.pay_method == 'weixin':
                res.update({
                    'weixin_pay_ids': [(6, 0, [weixin_pay.id for weixin_pay in order.weixin_pay_ids])]
                })
            if order.pay_method == 'alipay':
                res.update({
                    'alipay_ids': [(6, 0, [alipay.id for alipay in order.alipay_ids])]
                })
            refund_apply = refund_apply_obj.create(res)
            refund_apply_id = refund_apply.id

        # 向内网发送MQTT消息
        msg = {
            'action': 'cancel_reserve_record',
            'data': {
                'reserve_id': reserve_record.internal_id,  # 预约记录内部ID
                'refund_apply_id': refund_apply_id
            }
        }
        Emqtt.publish(order.company_id.topic, msg)

        if order.pay_method in ['free', 'coupon']:
            msg = '取消成功'
        else:
            msg = '取消成功，已支付的金额:%s元将在24小时内退回到你的%s账户中' % (order.amount_total, {'weixin': '微信', 'alipay': '支付宝'}[order.pay_method])
        return {
            'state': 1,
            'msg': msg
        }


    @http.route('/app/get_post_channel_category', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_post_channel_category(self):
        """获取频道分类"""
        post_channel_category_obj = request.env['hrp.post_channel_category'].sudo()

        post_channel_categories = post_channel_category_obj.search([('attribute', '=', '1')], order='id')

        res = []

        for post_channel_category in post_channel_categories:
            res.append({
                'id': post_channel_category.id,
                'name': post_channel_category.name
            })

        return {'state': 1, 'data': res}


    @http.route('/app/get_post_tag', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_post_tag(self):
        """获取话题标签"""
        post_tag_obj = request.env['hrp.post_tag'].sudo()

        post_tags = post_tag_obj.search([])

        res = []

        for post_tag in post_tags:
            res.append({
                'id': post_tag.id,
                'name': post_tag.name
            })

        return {'state': 1, 'data': res}


    @http.route([
        '/app/get_post_channel',
        '/app/get_news_channel'
    ], type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_post_channel(self):
        """获取频道"""
        post_channel_obj = request.env['hrp.post_channel'].sudo()

        data = request.jsonrequest['data']

        category_id = data['category_id']
        page = data.get('page', 1)

        # 分页显示
        page_num = 5

        if page < 0:
            return {'state': 0, 'msg': '页数错误'}

        offset = page_num * (page - 1)
        post_channels = post_channel_obj.search([('category_id', '=', category_id)], limit=page_num, offset=offset, order='create_date desc')

        res = {
            'current_page': page,
            'channels': []
        }

        for post_channel in post_channels:
            res['channels'].append({
                'id': post_channel.id,
                'name': post_channel.name,
                'image': '/web/image/hrp.post_channel/%s/image' % post_channel.id,
                'introduction': post_channel.introduction
            })

        return {'state': 1, 'data': res}

    @http.route('/app/get_my_post_channel', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_my_post_channel(self):
        """获取我的频道"""
        post_channel_obj = request.env['hrp.post_channel'].sudo()
        partner_obj = request.env['res.partner'].sudo()

        data = request.jsonrequest['data']

        partner_id = data['partner_id']
        page = data.get('page', 1)

        # 分页显示
        page_num = 5

        if page < 0:
            return {'state': 0, 'msg': '页数错误'}

        partner = partner_obj.search([('id', '=', partner_id)])
        if not partner:
            return {'state': 0, 'msg': '用户不存在'}

        offset = page_num * (page - 1)
        post_channels = post_channel_obj.search([('id', 'in', partner.post_channel_ids.ids)], limit=page_num, offset=offset, order='create_date desc')

        res = {
            'current_page': page,
            'channels': []
        }

        for post_channel in post_channels:
            res['channels'].append({
                'id': post_channel.id,
                'name': post_channel.name,
                'image': '/web/image/hrp.post_channel/%s/image' % post_channel.id,
                'introduction': post_channel.introduction
            })

        return {'state': 1, 'data': res}


    @http.route([
        '/app/get_post',
        '/app/get_news_post'
    ], type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_post(self):
        """获取话题"""
        post_obj = request.env['hrp.post'].sudo()

        data = request.jsonrequest['data']

        channel_id = data['channel_id']

        tag_id = data.get('tag_id')
        page = data.get('page', 1)

        # 默认显示5条
        page_num = 5

        offset = page_num * (page - 1)

        args = [('channel_id', '=', channel_id)]
        if tag_id:
            args += [('tag_ids', 'in', [tag_id])]

        posts = post_obj.search(args, limit=page_num, offset=offset, order='create_date desc')

        res = {
            'current_page': page,
            'posts': []
        }

        for post in posts:
            images = [] # 图片：最多显示3张
            for content in post.content_ids:
                if not content.is_main:
                    continue
                for image in content.image_ids:
                    if len(images) >= 3:
                        break
                    images.append('/web/image/hrp.post_content_image/%s/image' % image.id)
            res['posts'].append({
                'id': post.id,
                'name': post.title,
                'images': images,
                'create_time': (datetime.now() + timedelta(hours=8)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            })

        return {'state': 1, 'data': res}

    @http.route('/app/get_post_content', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_post_content(self):
        """获取话题内容"""
        post_obj = request.env['hrp.post'].sudo()
        post_content_obj = request.env['hrp.post_content'].sudo()

        data = request.jsonrequest['data']

        post_id = data['post_id']
        page = data.get('page', 1)

        post = post_obj.search([('id', '=', post_id)])
        if not post:
            return {'state': 0, 'msg': '话题错误'}

        # 默认显示5条
        page_num = 5

        offset = page_num * (page - 1)

        post_contents = post_content_obj.search([('post_id', '=', post_id)], limit=page_num, offset=offset, order='create_date desc')

        res = {
            'current_page': page,
            'post': {
                'post_title': post.title,
                'owner': post.partner_id.name,
                'post_contents': []
            }
        }

        for post_content in post_contents:
            images = []
            for image in post_content.image_ids:
                images.append('/web/image/hrp.post_content_image/%s/image' % image.id)

            res['post']['post_contents'].append({
                'id': post_content.id,
                'partner_id': post_content.partner_id.id,
                'partner_name': post_content.partner_id.name,
                'is_owner': True if post_content.partner_id == post.partner_id else False,
                'content': post_content.content,
                'images': images,
                'parent_id': post_content.parent_id.id
            })

        return {'state': 1, 'data': res}


    @http.route('/app/create_post', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def create_post(self):
        """新建话题"""
        post_obj = request.env['hrp.post'].sudo()
        post_tag_obj = request.env['hrp.post_tag'].sudo()
        post_channel_obj = request.env['hrp.post_channel'].sudo()
        partner_obj = request.env['res.partner'].sudo()
        post_content_obj = request.env['hrp.post_content'].sudo()

        data = request.jsonrequest['data']

        channel_id = data['channel_id']
        title = data['title']
        partner_id = data['partner_id']
        tag_ids = data['tag_ids']
        content = data['content']

        images = data.get('images', [])

        if not post_channel_obj.search([('id', '=', channel_id)]):
            return {'state': 0, 'msg': '频道错误'}

        if not partner_obj.search([('id', '=', partner_id)]):
            return {'state': 0, 'msg': '用户不存在'}

        # 标签
        post_tags = post_tag_obj.search([('id', 'in', tag_ids)])
        if not post_tags:
            return {'state': 0, 'msg': '标签错误'}

        # 创建话题
        post = post_obj.create({
            'channel_id': channel_id,
            'title': title,
            'partner_id': partner_id,
            'tag_ids': [(6, 0, post_tags.ids)]
        })
        # 创建主内容
        post_content_obj.create({
            'post_id': post.id,
            'partner_id': partner_id,
            'content': content
        })

        return {'state': 1, 'data': {'post_id': post.id}}

    @http.route([
        '/app/create_post_content',
        '/app/create_news_comment'
    ], type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def create_post_content(self):
        """发表话题内容"""
        post_obj = request.env['hrp.post'].sudo()
        partner_obj = request.env['res.partner'].sudo()
        post_content_obj = request.env['hrp.post_content'].sudo()
        post_content_image_obj = request.env['hrp.post_content_image'].sudo()

        data = request.jsonrequest['data']

        post_id = data['post_id']
        partner_id = data['partner_id']
        content = data['content']

        images = data.get('images', [])
        parent_id = data.get('parent_id')

        if not post_obj.search([('id', '=', post_id)]):
            return {'state': 0, 'msg': '话题错误'}

        if not partner_obj.search([('id', '=', partner_id)]):
            return {'state': 0, 'msg': '用户不存在'}

        if parent_id and not post_content_obj.search([('id', '=', parent_id)]):
            return {'state': 0, 'msg': '回复错误'}

        post_content = post_content_obj.create({
            'post_id': post_id,
            'partner_id': partner_id,
            'content': content,
            'parent_id': parent_id
        })

        # 图片处理
        try:
            for image in images:
                post_content_image_obj.create({
                    'post_content_id': post_content.id,
                    'image': image
                })
        except Exception:
            _logger.error(traceback.format_exc())
            return {'state': 0, 'msg': '图片存储失败'}

        return {'state': 1, 'data': {'post_content_id': post_content.id}}


    @http.route('/app/follow_channel', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def follow_channel(self):
        """关注频道"""
        channel_obj = request.env['hrp.post_channel'].sudo()
        partner_obj = request.env['res.partner'].sudo()

        data = request.jsonrequest['data']

        channel_id = data['channel_id']
        partner_id = data['partner_id']

        channel = channel_obj.search([('id', '=', channel_id)])

        if not channel:
            return {'state': 0, 'msg': '频道错误'}

        partner = partner_obj.search([('id', '=', partner_id)])
        if not partner:
            return {'state': 0, 'msg': '用户不存在'}

        partner.write({
            'post_channel_ids': [(4, channel_id)]
        })

        return {'state': 1}

    @http.route('/app/cancel_follow_channel', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def cancel_follow_channel(self):
        """取消关注频道"""
        channel_obj = request.env['hrp.post_channel'].sudo()
        partner_obj = request.env['res.partner'].sudo()

        data = request.jsonrequest['data']

        channel_id = data['channel_id']
        partner_id = data['partner_id']

        channel = channel_obj.search([('id', '=', channel_id)])

        if not channel:
            return {'state': 0, 'msg': '频道错误'}

        partner = partner_obj.search([('id', '=', partner_id)])
        if not partner:
            return {'state': 0, 'msg': '用户不存在'}

        partner.write({
            'post_channel_ids': [(3, channel_id)]
        })

        return {'state': 1}

    @http.route('/app/get_follow_channel', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_follow_channel(self):
        """获取关注频道"""
        partner_obj = request.env['res.partner'].sudo()

        data = request.jsonrequest['data']

        partner_id = data['partner_id']

        partner = partner_obj.search([('id', '=', partner_id)])
        if not partner:
            return {'state': 0, 'msg': '用户不存在'}

        res = []

        for channel in partner.post_channel_ids:
            res.append({
                'id': channel.id,
                'name': channel.name,
            })

        return {'state': 1, 'data': res}


    @http.route('/app/collect_post', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def collect_post(self):
        """收藏话题"""
        post_obj = request.env['hrp.post'].sudo()
        partner_obj = request.env['res.partner'].sudo()

        data = request.jsonrequest['data']

        post_id = data['post_id']
        partner_id = data['partner_id']

        post = post_obj.search([('id', '=', post_id)])

        if not post:
            return {'state': 0, 'msg': '话题错误'}

        partner = partner_obj.search([('id', '=', partner_id)])
        if not partner:
            return {'state': 0, 'msg': '用户不存在'}

        partner.write({
            'post_ids': [(4, post_id)]
        })

        return {'state': 1}

    @http.route('/app/cancel_collect_post', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def cancel_collect_post(self):
        """取消关注频道"""
        post_obj = request.env['hrp.post'].sudo()
        partner_obj = request.env['res.partner'].sudo()

        data = request.jsonrequest['data']

        post_id = data['post_id']
        partner_id = data['partner_id']

        post = post_obj.search([('id', '=', post_id)])

        if not post:
            return {'state': 0, 'msg': '话题错误'}

        partner = partner_obj.search([('id', '=', partner_id)])
        if not partner:
            return {'state': 0, 'msg': '用户不存在'}

        partner.write({
            'post_ids': [(3, post_id)]
        })

        return {'state': 1}

    @http.route('/app/get_collect_post', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_collect_post(self):
        """获取收藏的话题"""
        partner_obj = request.env['res.partner'].sudo()

        data = request.jsonrequest['data']

        partner_id = data['partner_id']

        partner = partner_obj.search([('id', '=', partner_id)])
        if not partner:
            return {'state': 0, 'msg': '用户不存在'}

        res = []

        for post in partner.post_ids:
            res.append({
                'id': post.id,
                'title': post.title,
            })

        return {'state': 1, 'data': res}

    @http.route('/app/get_news_channel_category', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_news_channel_category(self):
        """获取新闻频道分类"""
        post_channel_category_obj = request.env['hrp.post_channel_category'].sudo()

        post_channel_categories = post_channel_category_obj.search([('attribute', '=', '2')], order='id')

        res = []

        for post_channel_category in post_channel_categories:
            res.append({
                'id': post_channel_category.id,
                'name': post_channel_category.name
            })

        return {'state': 1, 'data': res}

    @http.route('/app/get_news_content', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_news_content(self):
        """获取新闻内容"""
        post_obj = request.env['hrp.post'].sudo()
        post_content_obj = request.env['hrp.post_content'].sudo()

        data = request.jsonrequest['data']

        post_id = data['post_id']

        post = post_obj.search([('id', '=', post_id)])
        if not post:
            return {'state': 0, 'msg': '话题错误'}


        post_content = post_content_obj.search([('post_id', '=', post_id), ('is_main', '=', True)], limit=1)

        res = {
            'title': post.title,
            'news_url': post_content.url
        }

        return {'state': 1, 'data': res}


    @http.route('/app/get_news_comment', type='json', auth="public", methods=['POST'], cors='*', csrf=False)
    @interface_wraps
    def get_news_comment(self):
        """获取新闻评论"""
        post_obj = request.env['hrp.post'].sudo()
        post_content_obj = request.env['hrp.post_content'].sudo()

        data = request.jsonrequest['data']

        post_id = data['post_id']
        page = data.get('page', 1)

        post = post_obj.search([('id', '=', post_id)])
        if not post:
            return {'state': 0, 'msg': '话题错误'}

        # 默认显示10条
        page_num = 10

        offset = page_num * (page - 1)

        post_contents = post_content_obj.search([('post_id', '=', post_id), ('is_main', '=', False)], limit=page_num, offset=offset,
                                                order='create_date desc')

        res = {
            'current_page': page,
            'post_contents': []
        }

        for post_content in post_contents:
            images = []
            for image in post_content.image_ids:
                images.append('/web/image/hrp.post_content_image/%s/image' % image.id)

            res['post_contents'].append({
                'id': post_content.id,
                'partner_id': post_content.partner_id.id,
                'partner_name': post_content.partner_id.name or '',
                'content': post_content.content or '',
                'images': images,
                'parent_id': post_content.parent_id.id
            })

        return {'state': 1, 'data': res}

