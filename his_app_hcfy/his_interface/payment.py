# -*- encoding:utf-8 -*-
from datetime import datetime

from odoo import fields
from odoo import models
from odoo.addons.his_app_hcfy.his_interface.his_interface import his_interface_wrap
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, config


class Payment(models.TransientModel):
    _inherit = 'his.interface'
    _description = '缴费相关接口'

    @his_interface_wrap('5001', pass_user_id=True)
    def get_payment_list(self, partner_id):
        """查询未缴费明细
        @param partner_id: 患者ID
        @return: [{
            receipt_no: 单据号,
            exec_dept: 执行科室,
            price_subtotal: 小计,
            details:[{
                product_id: 收费项目内部ID,
                name: 项目名称,
                price: 单价,
                qty: 数量,
                unit: 单位,
                amount: 金额,
                fees_name: 收据费目
            }]
        }]
        传入:
        <Request>
            <TransCode>5001</TransCode>
            <PatientID>1562356</PatientID>
            <ReceiptNo></ReceiptNo>
        </Request>
        返回:
        <Response>
            <TransCode>5001</TransCode>
            <ResultCode>0</ResultCode>
            <ErrorMsg></ErrorMsg>
            <List>
                <Item>
                    <ReceiptNo>单据号</ReceiptNo>
                    <ReceiptTime>开单时间</ReceiptTime>
                    <BillDept>开单部门</BillDept>
                    <ExecDept>执行部门</ExecDept>
                    <Doctor>医生姓名</Doctor>
                    <FeesType>费别</FeesType>
                    <FeesItem>收据费目</FeesItem>
                    <GroupID>诊疗项目ID</GroupID>
                    <GroupName>诊疗项目名称</GroupName>
                    <ItemID>收费ID</ItemID>
                    <ItemName>收费名称</ItemName>
                    <ItemUnit>计量单位</ItemUnit>
                    <Num>数量</Num>
                    <Price>单价</Price>
                    <ShouldMoney>应收金额</ShouldMoney>
                    <ActualMoney>实收金额</ActualMoney>
                    <CenterCode>医保编码</CenterCode>
                    <BillDeptID>开单科室编码</BillDeptID>
                </Item>
            </List>
        </Response>
        """
        if getattr(self, 'process_to_his_data'):
            partner = self.env['res.partner'].sudo().browse(partner_id)
            return {'PatientID': partner.his_id, 'ReceiptNo': ''}

        product_obj = self.env['product.template'].sudo()
        his_return_dict = getattr(self, 'process_his_return_data')
        result = his_return_dict['List']['Item']
        if isinstance(result, dict):
            result = [result]

        # 根据单据号分组
        group_receipt_no = {}
        for res in result:
            group_receipt_no.setdefault(res['ReceiptNo'], []).append(res)

        get_product_id = lambda his_id: product_obj.search([('his_id', '=', his_id)]).id

        result = []
        for receipt_no in group_receipt_no:
            payment_list = group_receipt_no[receipt_no]

            result.append({
                'receipt_no': receipt_no, # 单据号
                'exec_dept': payment_list[0]['ExecDept'], # 执行科室
                'price_subtotal': sum([item['ActualMoney'] for item in payment_list]), # 小计
                'details': [
                    {
                        'product_id': get_product_id(item['ItemCode']), # 收费项目内部ID TODO ItemId => ItemCode
                        # 'product_id': get_product_id(item['ItemID']), # 收费项目内部ID
                        'name': item['ItemName'],  # 项目名称
                        'price': item['Price'],  # 单价
                        'qty': item['Num'],  # 数量
                        'unit': item['ItemUnit'],  # 单位
                        'amount': item['ActualMoney'],  # 金额
                        'fees_name': item['FeesItem'],  # 收据费目
                    } for item in payment_list], # 缴费明细
            })

        return result


    @his_interface_wrap('5002', pass_user_id=True)
    def payment_commit_his(self, orders):
        """自助缴费
        @param orders: 待提交的订单
        @return
        传入:
        <Request>
            <TransCode>5002</TransCode>
            <CardTypeID>卡类型ID</CardTypeID>
            <CardNo>卡号</CardNo>
            <Password>密码</Password>
            <PatientID>卡号</PatientID>
            <UserId>机器号</UserId>
            <ReceiptNo>单据号</ReceiptNo>
            <List>
                <PayType>支付类型</PayType>
                <PayMode>支付方式</PayMode>
                <PayAmt>支付金额</PayAmt>
                <PayNo>支付流水号</PayNo>
                <PayCardNo>支付卡号</PayCardNo>
                <PayNote>支付说明</PayNote>
                <ExpandList>
                    <ItemName>项目名</ItemName>
                    <ItemValue>项目值</ItemValue>
                </ExpandList>
            </List>
            (医保信息省略)
        </Request>
        传出:
        <Response>
            <TransCode>5002</TransCode>
            <ResultCode>0</ResultCode>
            <ErrorMsg></ErrorMsg>
            <TranFlow>医院流水号</TranFlow>
            <TranTime>交易时间</TranTime>
            <SendWin>发药窗口</SendWin>
        </Response>
        """

        if getattr(self, 'process_to_his_data'):
            receipt_nos = ','.join([order.receipt_no for order in orders]) # 单据号
            amount_total = sum([order.amount_total for order in orders]) # 支付金额
            order = orders[0]
            partner = order.partner_id # 患者

            # 支付流水号、支付方式
            if order.pay_method == 'weixin':
                trade_no = order.weixin_pay_ids[0].transaction_id # 微信支付订单号
                pay_mode = config['weixin_card_type_id'] # 支付方式
                # pay_card_no = ''
            elif order.pay_method == 'alipay':
                trade_no = order.alipay_ids[0].trade_no  # 支付宝交易号
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

            res = {
                'CardTypeID': card_type_id,  # 卡类型ID(2002.CardTypeID（身份识别）)
                'CardNo': card_no,  # 卡号
                'Password': '',  # 密码
                'PatientID': partner.his_id,  # 病人ID
                'ReceiptNo': receipt_nos, # 单据号
                'List': {
                    'Item': [{
                        'PayType': '3',  # 支付类型, 0、现金 1、预交 2、消费卡 3、三方 4、医保
                        'PayMode': pay_mode,  # 支付方式, 医保基金，个人帐户，现金, 三方支付时为（2002.CardTypeID（帐户支付））
                        'PayAmt': amount_total,  # 支付金额, 两位小数
                        'PayNo': trade_no,  # 支付流水号,
                        'PayCardNo': order.pay_method,  # 支付卡号,
                        'PayNote': '',  # 支付说明,
                    }]
                }
            }

            return res

        his_return_dict = getattr(self, 'process_his_return_data')
        # return his_return_dict['TranFlow'] # 医院结算流水号
        return {
            'tran_flow': his_return_dict['TranFlow'], # 医院结算流水号
            # 'tran_time': his_return_dict['TranTime'], # 交易时间
            # 'send_win': his_return_dict['SendWin'],  # 发药窗口
        }


    @his_interface_wrap('5003', pass_user_id=True)
    def get_payment_record(self, partner_id, start_date, end_date):
        """查询已缴费接口"""
        if getattr(self, 'process_to_his_data'):
            partner = self.env['res.partner'].sudo().browse(partner_id)
            return {
                'PatientID': partner.his_id,
                'StartDate': start_date,
                'EndDate': end_date,
                'Start': 1,
                'RequestQty': 1000
            }

        his_return_dict = getattr(self, 'process_his_return_data')
        result = his_return_dict['List']['Item']
        if isinstance(result, dict):
            result = [result]

        # 根据单据号分组
        group_receipt_no = {}
        for res in result:
            group_receipt_no.setdefault(res['ReceiptNo'], []).append(res)

        result = []
        for receipt_no in group_receipt_no:
            payment_list = group_receipt_no[receipt_no]
            price_subtotal = sum([float(item['ActualMoney']) for item in payment_list]) # 小计

            # 按收据费目分组
            group_fees_name = {}
            for item in payment_list:
                group_fees_name.setdefault(item['FeesItem'], []).append(item)

            details = []
            for fees_name in group_fees_name:
                details.append({
                    'amount': sum([float(item['ActualMoney']) for item in group_fees_name[fees_name]]),  # 金额
                    'fees_name': fees_name,  # 收据费目
                })

            receipt_time = payment_list[0]['ReceiptTime'].split()[0]
            receipt_time = receipt_time.replace('/', '-')
            receipt_time = datetime.strptime(receipt_time, DEFAULT_SERVER_DATE_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
            result.append({
                'receipt_no': receipt_no, # 单据号
                'receipt_time': receipt_time, # 开单时间
                'exec_dept': payment_list[0]['ExecDept'], # 执行科室
                'price_subtotal': price_subtotal, # 小计
                'details': details, # 缴费明细
            })

            result.sort(key=lambda x: x['receipt_time'], reverse=True)

        return result


    @his_interface_wrap('3001', pass_user_id=True)
    def recharge_commit_his(self, order):
        """预交金充值"""
        if getattr(self, 'process_to_his_data'):
            partner = order.partner_id # 患者

            # 支付流水号、支付方式
            if order.pay_method == 'weixin':
                trade_no = order.weixin_pay_ids[0].transaction_id # 微信支付订单号
                pay_mode = config['weixin_card_type_id'] # 支付方式
            elif order.pay_method == 'alipay':
                trade_no = order.alipay_ids[0].trade_no  # 支付宝交易号
                pay_mode = config['alipay_card_type_id'] # 支付方式
            elif order.pay_method == 'longpay':
                trade_no = order.long_pay_record_ids[0].ORDERID  # 龙支付定单号
                pay_mode = config['longpay_card_type_id'] or config['alipay_card_type_id'] # 支付方式
            else:
                trade_no = ''
                pay_mode = ''

            card_type_id = partner.card_type_id
            card_no = ''
            if card_type_id == config['identity_card_type_id']:
                card_no = partner.id_no
            elif card_type_id == config['medical_card_type_id']:
                card_no = partner.medical_no
            elif card_type_id == config['treatment_card_type_id']:
                card_no = partner.card_no

            res = {
                'CardTypeID': card_type_id,  # 卡类型ID(2002.CardTypeID（身份识别）)
                'CardNo': card_no,  # 卡号
                'PatientID': partner.his_id,  # 病人ID
                'PayCardTypeID': pay_mode,  # 支付卡类型ID, 0、现金 1、预交 2、消费卡 3、三方 4、医保
                'Amt': order.amount_total, # 充值金额
                'YJtype': order.recharge_type, # 预交类型
                'PayCardNo': order.pay_method, # 支付卡号
                'SerNo': trade_no,  # 对账流水号,
            }

            return res

        his_return_dict = getattr(self, 'process_his_return_data')
        return {
            'tran_flow': his_return_dict['TranFlow'], # 医院交易流水号
            'mz_balance': his_return_dict['MzBalance'], # 门诊帐户余额
            'zy_balance': his_return_dict['ZyBalance'],  # 住院帐户余额
        }


    @his_interface_wrap('3003', pass_user_id=True)
    def get_recharge_record(self, partner_id, start_date, end_date, recharge_type):
        """查询充值记录"""
        if getattr(self, 'process_to_his_data'):
            partner = self.env['res.partner'].sudo().browse(partner_id)
            return {
                'PatientID': partner.his_id,
                'StartDate': start_date,
                'EndDate': end_date,
                'YJtype': recharge_type,
                'Start': 1,
                'RequestQty': 1000
            }

        his_return_dict = getattr(self, 'process_his_return_data')
        result = his_return_dict['List']['Item']
        if isinstance(result, dict):
            result = [result]

        res = []
        for item in result:
            res.append({
                'receipt_no': item['RegisterNo'],
                'recharge_time': item['JZTime'],
                'amount': item['Amt']
            })

        return res

    @his_interface_wrap('9016', pass_user_id=False)
    def service_commit_his(self, order):
        """划价提交HIS"""
        if getattr(self, 'process_to_his_data'):
            return {
                'PatientID': order.partner_id.his_id,
                'ZXDeptID': order.convenient_item_id.package_detail_ids[0].department_id.his_id,
                'List': {
                    'Item': [{
                        'FeeID': line.product_id.his_id,  # 收据费目ID
                        'Price': line.product_id.list_price,  # 现价
                        'Count': line.product_uom_qty,  # 实收数量
                        'TotalMoney': line.price_subtotal,  # 实收金额,
                    }for line in order.order_line]
                }
            }

        his_return_dict = getattr(self, 'process_his_return_data')
        return {
            'tran_flow': his_return_dict['TranFlow'], # 单据号
        }







