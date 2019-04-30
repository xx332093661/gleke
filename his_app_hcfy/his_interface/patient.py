# -*- encoding:utf-8 -*-
from datetime import datetime

from odoo import models
from odoo.addons.his_app_hcfy.his_interface.his_interface import his_interface_wrap
from odoo.tools import config


class Patient(models.TransientModel):
    _inherit = 'his.interface'
    _description = '患者相关接口'

    # @his_interface_wrap('2001')
    # def id_no_exist(self, id_no):
    #     """查询身份证是否办过就诊卡
    #     @param id_no: 身份证号
    #     @return: {
    #         'state': 是否可办卡(0-未办过, 1-已办过卡)
    #     }
    #
    #     传入:
    #     <Request>
    #         <TransCode>2001</TransCode>
    #         <IDCardNo>身份证号</IDCardNo>
    #     </Request>
    #     返回:
    #     <Response>
    #         <TransCode>2001</TransCode>
    #         <ResultCode>0</ResultCode>
    #         <ErrorMsg></ErrorMsg>
    #         <Status>0</Status>
    #     </Response>
    #     """
    #     if getattr(self, 'process_to_his_data'):
    #         return {'IDCardNo': id_no}
    #
    #     his_return_dict = getattr(self, 'process_his_return_data')
    #     return {'state': his_return_dict['Status']}

    @his_interface_wrap('2003')
    def id_no_exist(self, id_no):
        """查询身份证是否办过就诊卡
        @param id_no: 身份证号
        @return: {
            'state': 是否可办卡(0-未办过, 1-已办过卡)
        }

        传入:
        <Request>
            <TransCode>2001</TransCode>
            <IDCardNo>身份证号</IDCardNo>
        </Request>
        返回:
        <Response>
            <TransCode>2001</TransCode>
            <ResultCode>0</ResultCode>
            <ErrorMsg></ErrorMsg>
            <Status>0</Status>
        </Response>
        """

        if getattr(self, 'process_to_his_data'):
            return {'CardTypeID': config['identity_card_type_id'], 'CardNo': id_no}

        his_return_dict = getattr(self, 'process_his_return_data')
        return {'state': his_return_dict['Status']}

        # if getattr(self, 'process_to_his_data'):
        #     return {'IDCardNo': id_no}
        #
        # his_return_dict = getattr(self, 'process_his_return_data')
        # return {'state': his_return_dict['Status']}


    @his_interface_wrap('2002')
    def get_card_type(self, request_type):
        """查询医院所支持的卡类别
        @param request_type: 请求类型 1、身份识别 2、账户支付
        @return: [{
            'card_type_id': 卡类别ID,
            'card_type_name': 卡类别名称,
            'insure_id': 医保类别ID,
            'insure_name': 医保名称
        }]
        select a.id,a.名称,a.险类,b.名称 as 险类名称 from 医疗卡类别 a,保险类别 b where a.险类=b.序号(+)
        传入:
        <Request>
            <TransCode>2002</TransCode>
            <RquestType>1</RquestType>
        </Request>
        返回:
        <Response>
            <TransCode>2001</TransCode>
            <ResultCode>0</ResultCode>
            <ErrorMsg></ErrorMsg>
            <List>
                <Item>
                    <CardTypeID>1</CardTypeID>
                    <CardTypeName>就诊卡</CardTypeName>
                    <InsureId></InsureId>
                    <InsureName></InsureName>
                </Item>
                <Item>
                    <CardTypeID>1</CardTypeID>
                    <CardTypeName>就诊卡</CardTypeName>
                    <InsureId></InsureId>
                    <InsureName></InsureName>
                </Item>
            </List>
        </Response>
        """
        if getattr(self, 'process_to_his_data'):
            return {'RquestType': request_type}

        his_return_dict = getattr(self, 'process_his_return_data')
        result = his_return_dict['List']['Item']
        if isinstance(result, dict):
            result = [result]

        return [
            {
                'card_type_id': res['CardTypeID'],
                'card_type_name': res['CardTypeName'],
                'insure_id': res['InsureId'],
                'insure_name': res['InsureName'],

            } for res in result]

    @his_interface_wrap('2003')
    def medical_no_exist(self, medical_no):
        """查询医保卡是否办过就诊卡"""
        if getattr(self, 'process_to_his_data'):
            return {'CardTypeID': config['medical_card_type_id'], 'CardNo': medical_no}

        his_return_dict = getattr(self, 'process_his_return_data')
        return {'state': his_return_dict['Status']}

    @his_interface_wrap('2004', pass_user_id=True)
    def add_patient(self, name, sex, identity_no, phone, birthday, card_no, card_type_id, age):
        """用就诊卡签约办卡

        @return: {
            'his_id': HISID
        }
        传入:
        <Request>
            <TransCode>2004</TransCode>
            <CardTypeID>卡类别ID(2002.CardTypeID(身份识别))</CardTypeID>
            <CardNo>(就诊、工行、医保)卡号</CardNo>
            <PatientName>病人姓名</PatientName>
            <Sex>性别(男，女，未知)</Sex>
            <Birthday>出生日期(YYYY-MM-DD)</Birthday>
            <Age>年龄(25岁，3月10天等等)</Age>
            <IDCardNo>身份证号</IDCardNo>
            <PayCardTypeID>支付卡类型ID(2002.CardTypeID(帐户支付)（0 现金 2 三方账户转账【或电子钱包类、公交卡等】）)</PayCardTypeID>
            <Amt>预交金金额</Amt>
            <Tel>手机号码</Tel>
            <UserId>机器号</UserId>
            <SerNo>对账流水号</SerNo>
            <Password>未加密（明文：123456），可设置4位密码</Password>
        </Request>
        返回:
        <Response>
            <TransCode>2004</TransCode>
            <ResultCode>0</ResultCode>
            <ErrorMsg></ErrorMsg>
            <PatientID><病人ID/PatientID>
            <CardTranFlow>办卡流水号</CardTranFlow>
            <PayTranFlow>预交流水号</PayTranFlow>
            <TranTime>办卡时间</TranTime>
            <Amt>卡余额</Amt>
        </Response>
        """

        if getattr(self, 'process_to_his_data'):
            return {
                'CardTypeID': card_type_id,
                'CardNo': card_no,
                'PatientName': name,
                'Sex': sex,
                'Birthday': birthday,
                'Age': age,
                'IDCardNo': identity_no or '',
                'PayCardTypeID': '',
                'Amt': 0,
                'Tel': phone or '',
                'SerNo': '',
                'Password': ''
            }

        his_return_dict = getattr(self, 'process_his_return_data')
        return {
            'his_id': his_return_dict['PatientID']
        }


    @his_interface_wrap('2006', pass_user_id=True)
    def get_patient_info(self, card_no, card_type_id):
        """根据卡号号获取病人信息
        @param card_no: 卡号
        @param card_type_id: 卡类型id
        @return: {
            'his_id': HISID,
        }
        传入:
        <Request>
            <TransCode>2006</TransCode>
            <CardTypeID>卡类别ID(2002.CardTypeID(身份识别))</CardTypeID>
            <CardNo>卡号</CardNo>
            <UserId>机器号</UserId>
        </Request>
        返回:
        <Response>
            <TransCode>2006</TransCode>
            <ResultCode>0</ResultCode>
            <ErrorMsg></ErrorMsg>
            <PatientID><病人ID/PatientID>
            <PatName>姓名</PatName>
            <Birthday>生日</Birthday>
            <Age>病人年龄</Age>
            <PatSex>性别</PatSex>
            <IDCard>身份号码</IDCard>
            <AccBalance>门诊账户余额</AccBalance>
            <ZyBalance>住院账户余额</ZyBalance>
            <Tel>手机号码</Tel>
            <MedType>费别</MedType>
        </Response>
        """

        if getattr(self, 'process_to_his_data'):
            # return {
            #     'CardTypeID': config['identity_card_type_id'],
            #     'CardNo': id_no,
            # }
            return {
                'CardTypeID': card_type_id,
                'CardNo': card_no,
            }

        his_return_dict = getattr(self, 'process_his_return_data')
        return {
            'his_id': his_return_dict['PatientID'],
            'outpatient_num': his_return_dict['MZH'], # 门诊号
            'hospitalize_no': his_return_dict['ZYH'], # 住院号
            'card_no': his_return_dict['JZKH'] # 就诊卡号
        }




