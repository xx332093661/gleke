# -*- encoding:utf-8 -*-
from datetime import datetime, timedelta
import logging
from odoo import fields
from odoo import models
from odoo.addons.his_app_hcfy.his_interface.his_interface import his_interface_wrap
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, config


_logger = logging.getLogger(__name__)


class Register(models.TransientModel):
    _inherit = 'his.interface'
    _description = '挂号相关接口'

    @his_interface_wrap('4001')
    def get_register_type(self):
        """获取挂号类别
        @return: [号类名称1, 号类名称2, ...]
        select a.名称 from 号类 a where exists (select 1 from 挂号安排 b where a.名称=b.号类)
        union all select '急诊' from dual;
        传入:
        <Request>
            <TransCode>4001</TransCode>
        </Request>
        返回:
        <Response>
            <TransCode>4001</TransCode>
            <ResultCode>0</ResultCode>
            <ErrorMsg></ErrorMsg>
            <List>
                <Item>
                    <CardTypeName>号类名称</CardTypeName>
                </Item>
            </List>
        </Response>
        """
        if getattr(self, 'process_to_his_data'):
            return {}

        his_return_dict = getattr(self, 'process_his_return_data')
        result = his_return_dict['List']['Item']
        if isinstance(result, dict):
            result = [result]

        return [res['CardTypeName'] for res in result]


    @his_interface_wrap('4002', pass_user_id=True)
    def get_department(self, day, register_type):
        """查询能挂的科室列表
        @param day: 日期
        @param register_type: 号类名称
        @return: [科室ID, 科室ID, ...]

        传入:
        <Request>
            <TransCode>4002</TransCode>
            <RegType>预约类型,(1、挂号 2、预约挂号)</RegType>
            <Day>预约日期(YYYY-MM-DD，挂号为空)/Day>
            <RigsterType>挂号种类(4001.CardTypeName)</RigsterType>
            <Start>开始笔数</Start>
            <RequestQty>请求笔数</RequestQty>
            <UserId>机器号</UserId>
        </Request>
        返回:
        <Response>
            <TransCode>4002</TransCode>
            <ResultCode>0</ResultCode>
            <ErrorMsg></ErrorMsg>
            <Count>总共笔数</Count>
            <ReturnQty>返回笔数</ReturnQty>
            <List>
                <Item>
                    <DeptID>科室ID</DeptID>
                    <DeptName>科室名称</DeptName>
                </Item>
            </List>
        </Response>

        """

        if getattr(self, 'process_to_his_data'):
            return {
                'RegType': '1', # 挂号类型(1、挂号 2、预约挂号)
                'Day': day, # 预约日期(YYYY-MM-DD，挂号为空)
                'RigsterType': register_type, # 挂号种类(4001.CardTypeName)
                'Start': '1', # 开始笔数
                'RequestQty': '1000', # 请求笔数
            }

        department_obj = self.env['hr.department']
        get_department_id = lambda his_id: department_obj.search([('his_id', '=', his_id)]).id

        his_return_dict = getattr(self, 'process_his_return_data')
        departments = his_return_dict['List']['Item']
        if isinstance(departments, dict):
            departments = [departments]


        return [get_department_id(department['DeptID']) for department in departments]


    @his_interface_wrap('4003', pass_user_id=True)
    def get_register_employee(self, register_type, department_his_id):
        """查询能挂的科室医生列表
        @param register_type: 号类名称
        @param department_his_id: 科室的his_id
        @return: [{
            # 'department_id': 科室ID,
            'employee_id': 医生ID,
            'as_rowid': 号别,
            'product_ids': 产品IDS
        }]

        传入:
        <Request>
            <TransCode>4003</TransCode>
            <RegType>预约类型,(1、挂号 2、预约挂号)</RegType>
            <Day>预约日期(YYYY-MM-DD，挂号为空)/Day>
            <RigsterType>挂号种类(4001.CardTypeName)</RigsterType>
            <DeptID>科室ID</DeptID>
            <MedType>费别</MedType>
            <Start>开始笔数</Start>
            <RequestQty>请求笔数</RequestQty>
            <UserId>机器号</UserId>
        </Request>

        返回:
        <Response>
            <TransCode>4003</TransCode>
            <ResultCode>0</ResultCode>
            <ErrorMsg></ErrorMsg>
            <Count>总共笔数</Count>
            <ReturnQty>返回笔数</ReturnQty>
            <List>
                <Item>
                    <AsRowid>号码</AsRowid>
                    <MarkId>医生ID</MarkId>
                    <MarkDesc>医生姓名</MarkDesc>
                    <SessionType>出诊级别</SessionType>
                    <HBTime>出诊安排</HBTime>
                    <RegCount>预约挂号剩余总数</RegCount>
                    <Price>价格</Price>
                    <IsTime>是否启用时段(1、启用时段 2、未启用时段(若未启用时段则无需调用挂号安排时段查询))</IsTime>
                    <List1>
                        <Item1>
                            <ItemID>收费ID</ItemID>
                            <ItemName>收费名称</ItemName>
                            <ItemUnit>计量单位</ItemUnit>
                            <Num>数量</Num>
                            <Price>单价</Price>
                            <ShouldMoney>应收金额</ShouldMoney>
                            <ActualMoney>实收金额</ActualMoney>
                            <CenterCode>医保编码</CenterCode>
                            <BillDeptID>开单科室编码</BillDeptID>
                        </Item1>
                    </List1>
                </Item>
            </List>
        </Response>
        """

        if getattr(self, 'process_to_his_data'):
            # TODO MedType
            return {
                'RegType': '1', # 挂号类型(1、挂号 2、预约挂号)
                'Day': '', # 预约日期(YYYY-MM-DD，挂号为空)
                'RigsterType': register_type, # 挂号种类(4001.CardTypeName)
                'DeptID': department_his_id, # 科室ID
                'MedType': '', # 费别
                'Start': '1', # 开始笔数
                'RequestQty': '1000', # 请求笔数
            }

        employee_obj = self.env['hr.employee']
        product_obj = self.env['product.template']

        get_product_id = lambda his_id: product_obj.search([('code', '=', his_id)]).id

        his_return_dict = getattr(self, 'process_his_return_data')
        res = his_return_dict['List']['Item']
        if isinstance(res, dict):
            res = [res]

        result = []
        for r in res:
            register_fee = r['List1']['Item1'] # 挂号收费
            if isinstance(register_fee, dict):
                register_fee = [register_fee]

            product_ids = []
            for fee in register_fee:
                _logger.info(fee['ItemID'])
                product_id = get_product_id(fee['ItemID'])
                if product_id:
                    product_ids.append(product_id)

            result.append({
                # 'department_id': department.id,
                'employee_id': employee_obj.search([('his_id', '=', r['MarkId'])]).id,
                'as_rowid': r['AsRowid'],
                'register_type': register_type,
                'product_ids': product_ids
            })

        return result


    @his_interface_wrap('4005', pass_user_id=True)
    def reserve_record_commit_his(self, reserve_record):
        """预约挂号提交挂号

        @param reserve_record: 预约记录
        @return: {
            'tran_flow': 医院结算流水号,
            'register_no': 挂号单号,
            'outpatient_num': 门诊号
        }
        传入:
        <Request>
            <TransCode>4005</TransCode>
            <RegType>预约类型,(1、挂号 2、预约挂号)</RegType>
            <Day>预约日期/Day>
            <PatientID>病人ID</PatientID>
            <CardTypeID>卡类型ID(2002.CardTypeID（身份识别）)</CardTypeID>
            <CardNo>卡号</CardNo>
            <Password>密码</Password>
            <AsRowid>号码 4003.AsRowid</AsRowid>
            <TimeValue>预约时间点</TimeValue>
            <Pharmaceutical>药事服务费(0、不收取 1、收取)</Pharmaceutical>
            <List>
                <Item>
                    <PayType>支付类型, 0、现金 1、预交 2、消费卡 3、三方 4、医保</PayType>
                    <PayMode>支付方式, 医保基金，个人帐户，现金, 三方支付时为（2002.CardTypeID（帐户支付））</PayMode>
                    <PayAmt>支付金额, 两位小数</PayAmt>
                    <PayNo>支付流水号</PayNo>
                    <PayCardNo>支付卡号</PayCardNo>
                    <PayNote>支付说明</PayNote>
                </Item>
            </List>
            <UserId>机器号</UserId>
        </Request>
        返回:
        <Response>
            <TransCode>4005</TransCode>
            <ResultCode>0</ResultCode>
            <ErrorMsg></ErrorMsg>
            <TranFlow>医院结算流水号</TranFlow>
            <RegisterNo>挂号单号</RegisterNo>
            <AsRowid>号码</AsRowid>
            <JZTime>就诊时间(YYYY-MM-DD HH24:MI:SS)</JZTime>
            <JZNo>就诊序号</JZNo>
            <Type>预约种类(4001返回的号类名称)</Type>
            <PatName>病人姓名</PatName>
            <MZH>门诊号</MZH>
            <FeesType>费别</FeesType>
            <FeesItem>收据费目</FeesItem>
            <DeptName>就诊科室</DeptName>
            <DeptPro>部门专业</DeptPro>
            <Loc>就诊诊室</Loc>
            <RoomLoc>诊室位置</RoomLoc>
            <DoctorName>医生姓名</DoctorName>
            <SessionType>医生职务</SessionType>
            <RegTime>预约时间</RegTime>
        </Response>
        """

        if getattr(self, 'process_to_his_data'):
            schedule_department_employee_obj = self.env['his.schedule_department_employee'] # 科室排班人员
            today= (datetime.now() + timedelta(hours=8)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            partner = reserve_record.partner_id # 患者
            order = reserve_record.order_id # 预约记录对应的订单

            # 支付流水号、支付方式
            if order.pay_method == 'weixin':
                trade_no = order.weixin_pay_ids[0].transaction_id # 微信支付订单号
                pay_mode = config['weixin_card_type_id'] # 支付方式
                # pay_card_no = ''
            elif order.pay_method == 'alipay':
                trade_no = order.alipay_ids[0].trade_no  # 流水号
                pay_mode = config['alipay_card_type_id'] # 支付方式
                # pay_card_no = ''
            elif order.pay_method == 'longpay':
                trade_no = order.long_pay_record_ids[0].ORDERID  # 龙支付定单号
                pay_mode = config['longpay_card_type_id'] or config['alipay_card_type_id']  # 支付方式
                # pay_card_no = ''
            else:
                trade_no = ''
                pay_mode = ''
                # pay_card_no = ''

            card_type_id = partner.card_type_id
            card_no = ''
            if card_type_id == config['identity_card_type_id']:
                card_no = partner.id_no
            elif card_type_id == config['medical_card_type_id']:
                card_no = partner.medical_no
            elif card_type_id == config['treatment_card_type_id']:
                card_no = partner.card_no

            # 支付方式

            # TODO Pharmaceutical
            schedule_department_employee = schedule_department_employee_obj.search([('department_id', '=', reserve_record.department_id.id), ('employee_id', '=', reserve_record.employee_id.id)])
            if order.pay_method in ['weixin', 'alipay', '']:
                as_rowid = schedule_department_employee.as_rowid
            else:
                as_rowid = schedule_department_employee.free_as_rowid

            res = {
                'RegType': '1',  # 预约类型, 1、挂号 2、预约挂号
                'Day': today,  # 预约日期
                'PatientID': partner.his_id, # 病人ID
                'CardTypeID': card_type_id, # 卡类型ID(2002.CardTypeID（身份识别）)
                'CardNo': card_no, # 卡号
                'Password': '', # 密码
                'AsRowid': as_rowid, # 号码 4003.AsRowid
                'TimeValue': '', # 预约时间点
                'Pharmaceutical': '0', # 药事服务费(0、不收取 1、收取)
                'List': {
                    'Item': [{
                        'PayType': '3',  # 支付类型, 0、现金 1、预交 2、消费卡 3、三方 4、医保
                        'PayMode': pay_mode,  # 支付方式, 医保基金，个人帐户，现金, 三方支付时为（2002.CardTypeID（帐户支付））
                        'PayAmt': order.amount_total,  # 支付金额, 两位小数
                        # 'PayAmt': 3.5,  # 支付金额, 两位小数
                        'PayNo': trade_no,  # 支付流水号,
                        'PayCardNo': order.pay_method,  # 支付卡号,
                        'PayNote': '',  # 支付说明,
                    }]
                }
            }

            return res

        his_return_dict = getattr(self, 'process_his_return_data')
        return {
            'tran_flow': his_return_dict['TranFlow'], # 医院结算流水号
            'receipt_no': his_return_dict['RegisterNo'], # 挂号单号
            'outpatient_num': his_return_dict['MZH'],  # 门诊号
        }



