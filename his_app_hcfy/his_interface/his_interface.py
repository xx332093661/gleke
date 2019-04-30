# -*- encoding:utf-8 -*-
import json
import socket
import traceback
from functools import wraps
import xmltodict
import logging

from odoo import models

_logger = logging.getLogger(__name__)
socket_host = '1.1.1.212'
socket_port = 8088


class CallHisExcept(Exception):
    """调用HIS接口异常"""
    pass


class HisResponseExcept(Exception):
    """HIS响应异常"""
    pass


def check_int(data):
    """是否是整数检查"""
    if data[0] in ('-', '+'):
        return data[1:].isdigit()
    return data.isdigit()


def convert_data(data):
    if data is None:
        return None

    data = data.upper()
    if data == 'TRUE':
        return True

    if data == 'FALSE':
        return False

    if data in ['NONE', 'NULL']:
        return None

    if check_int(data):
        return int(data)

    try:
        return float(data)
    except ValueError:
        return data


def his_return_convert(data):
    """HIS返回的xml数据，能转换成数值的转换成数值，能转换成布尔值的转换成布尔值"""
    if isinstance(data, dict):
        for key in data.keys():
            # 下列字段不用转换
            # 挂号号码、收费项目代码、门诊号、就诊卡号、住院号、电话、身份证号、医保卡号、床号
            if key in ('AsRowid', 'ItemCode', 'MZH', 'JZKH', 'ZYH', 'Tel', 'IDCard', 'InsureNo', 'Bed'):
                continue

            if isinstance(data[key], (dict, list)):
                his_return_convert(data[key])
            else:
                data[key] = convert_data(data[key])

    if isinstance(data, list):
        for index, item in enumerate(data):
            if isinstance(item, (dict, list)):
                his_return_convert(item)
            else:
                data[index] = convert_data(item)


def call_his(to_his_xml):
    """调用HIS接口"""
    # 数据编码
    try:
        data = to_his_xml.encode('gb2312', 'ignore')
    except UnicodeEncodeError:
        _logger.error(u'传递到HIS的数据编码发生错误!')
        _logger.error(traceback.format_exc())
        raise CallHisExcept(u'数据通讯错误')
    # 连接socket, 发送数据
    try:
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 定义socket类型，网络通信，TCP
        my_socket.connect((socket_host, socket_port))  # 要连接的IP与端口
        my_socket.send(data)
    except socket.error:
        _logger.error(u'连接Socket或发送数据发生错误!')
        _logger.error(traceback.format_exc())
        raise CallHisExcept(u'数据通讯错误')

    # 接收数据
    res = ''
    while True:
        data = my_socket.recv(1024)
        index = data.find('<?')
        if index == -1:
            index = 0

        res += data[index:]
        res = res.strip()
        if res.strip()[-11:] == '</Response>':
            break

    # 关闭连接
    my_socket.close()
    res = res.decode('gb2312')
    return res


def his_interface_wrap(trans_code, pass_user_id=False):
    """传入HIS数据和HIS返回数据转换
    @param trans_code: 业务代码
    @param pass_user_id: 传递到HIS的参数是否要添加'UserId'字段
    @return:
    """
    def wrapper(func):
        @wraps(func)
        def my_wrapper(self, *args):

            def process_to_his_data():
                """对传入到HIS的数据进行进一步处理"""
                setattr(self, 'process_to_his_data', True)
                setattr(self, 'process_his_return_data', None)
                to_his_dict = func(self, *args)

                # 加入公共参数
                to_his_dict.update({'TransCode': trans_code})
                if pass_user_id:
                    to_his_dict.update({'UserId': self.env.user.company_id.his_user_id})

                to_his_dict = {'Request': to_his_dict}
                _logger.info(u'调用HIS.%s传递DICT数据:', trans_code)
                _logger.info(json.dumps(to_his_dict, ensure_ascii=False, encoding='utf8', indent=4))
                return xmltodict.unparse(to_his_dict, full_document=True)


            def process_his_return_data():
                """对HIS返回的数据进行进一步处理"""
                his_return_dict = json.loads(json.dumps(xmltodict.parse(from_his_xml)))['Response']
                _logger.info(u'调用HIS.%s返回DICT数据:', trans_code)
                _logger.info(json.dumps(his_return_dict, ensure_ascii=False, encoding='utf8', indent=4))

                result_code = his_return_dict['ResultCode']
                if result_code == '1':
                    raise HisResponseExcept(his_return_dict['ErrorMsg'])

                # 删除公共参数
                his_return_dict.pop('TransCode')
                his_return_dict.pop('ResultCode')
                his_return_dict.pop('ErrorMsg')

                # HIS返回的xml数据，能转换成数值的转换成数值，能转换成布尔值的转换成布尔值
                his_return_convert(his_return_dict)

                setattr(self, 'process_to_his_data', None)
                setattr(self, 'process_his_return_data', his_return_dict)

                result = func(self, *args)
                return result

            # 传递到HIS数据格式处理
            to_his_xml = process_to_his_data()
            # 调用HIS接口
            try:
                from_his_xml = call_his(to_his_xml)
                _logger.info(from_his_xml)
                # try:
                #     _logger.info('11111111')
                #     _logger.info(from_his_xml.decode('utf8'))
                # except:
                #     pass
                # try:
                #     _logger.info('22222222')
                #     _logger.info(from_his_xml.decode('gb2312'))
                # except:
                #     pass
                # try:
                #     _logger.info('33333333')
                #     _logger.info(from_his_xml.encode('utf8'))
                # except:
                #     pass
                # try:
                #     _logger.info('44444444')
                #     _logger.info(from_his_xml.encode('gb2312'))
                # except:
                #     pass
            except CallHisExcept:
                raise

            # HIS返回数据处理
            try:
                to_client = process_his_return_data()
            except HisResponseExcept:
                raise

            # 日志
            _logger.info(u'调用%s函数返回数据:%s', func.func_name, json.dumps(to_client, ensure_ascii=False, encoding='utf8'))

            return to_client

        return my_wrapper

    return wrapper


class HisInterface(models.TransientModel):
    _name = 'his.interface'
    _description = 'HIS数据接口'

