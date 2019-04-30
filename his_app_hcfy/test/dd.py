# -*- encoding:utf-8 -*-
import json
from  datetime import datetime, timedelta
import xmltodict

from_his_xml = u'''<?xml version="1.0" encoding="utf-8" ?>
<Response>
    <TransCode>4005</TransCode>
    <ResultCode>0</ResultCode>
    <ErrorMsg></ErrorMsg>
    <TranFlow>4047644</TranFlow>
    <RegisterNo>R0082711</RegisterNo>
    <AsRowid>041</AsRowid>
    <JZTime>2017-05-22 15:35:24</JZTime>
    <JZNo>1</JZNo>
    <Type>普通</Type>
    <PatName>测试</PatName>
    <MZH>680403</MZH>
    <FeesType>普通</FeesType>
    <FeesItem>,挂号费</FeesItem>
    <DeptName>儿科普通门诊</DeptName>
    <Loc>---</Loc>
    <DoctorName>陈波</DoctorName>
    <SessionType>*主治医师</SessionType>
    <RegTime>2017-05-22 15:35:24</RegTime>
    <AccBalance></AccBalance>
</Response>
'''



# his_return_dict = json.loads(json.dumps(xmltodict.parse(from_his_xml)))['Response']
# pa = 12
#
# a = '2013-01-01'
# str = '%Y-%m-%d'
# datetime.strptime(a, str)
# DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
# appointment_time = '2017-05-24 06:30:00'
# appointment_time = (datetime.strptime(appointment_time, DATETIME_FORMAT) + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M').split()
# message = '|'.join(appointment_time + ['CA0001', '王力']) # 就诊日期|时间点|预约号|医生名称
# print message
his_return_dict = {
    "ErrorMsg": None,
    "ResultCode": "0",
    "TransCode": "5003",
    "List": {
        "Item": [
            {
                "ItemID": "123202",
                "BillDept": "儿保门诊",
                "Doctor": "蒋泽明",
                "ShouldMoney": "0.12",
                "ItemName": "维生素C片",
                "Price": "0.03",
                "GroupName": "维生素C片 100mg*100片/瓶",
                "FeesType": "普通",
                "FeesItem": "西药费",
                "ActualMoney": "0.12",
                "ItemUnit": "片",
                "ReceiptNo": "R0347548",
                "Num": "4.00",
                "ReceiptTime": "2017/5/24 11:05:09",
                "GroupID": "144",
                "ExecDept": "西药房"
            },
            {
                "ItemID": "113062",
                "BillDept": "儿保门诊",
                "Doctor": "蒋泽明",
                "ShouldMoney": "0.03",
                "ItemName": "维生素B1片",
                "Price": "0.03",
                "GroupName": "维生素B1片 10mg*100片/瓶",
                "FeesType": "普通",
                "FeesItem": "西药费",
                "ActualMoney": "0.03",
                "ItemUnit": "片",
                "ReceiptNo": "R0347548",
                "Num": "1.00",
                "ReceiptTime": "2017/5/24 11:05:09",
                "GroupID": "136",
                "ExecDept": "西药房"
            }
        ]
    }
}

result = his_return_dict['List']['Item']
if isinstance(result, dict):
    result = [result]

group_receipt_no = {}
for res in result:
    group_receipt_no.setdefault(res['ReceiptNo'], []).append(res)

result = []
for receipt_no in group_receipt_no:
    payment_list = group_receipt_no[receipt_no]
    mm = [float(item['ActualMoney']) for item in payment_list]
    price_subtotal = sum(mm)  # 小计

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

    result.append({
        'receipt_no': receipt_no,  # 单据号
        'exec_dept': payment_list[0]['ExecDept'],  # 执行科室
        'price_subtotal': price_subtotal,  # 小计
        'details': details,  # 缴费明细
    })

print result

mm = [0.15, 0.3]
a = sum(mm)
b = 1


mmm = '''
{
    "visit_date": "2017-05-25",
    "partner_id": 3206,
    "treatment_details": [
        {
            "queue_state_code": 0,
            "wait_count": 0,
            "reserve_department_id": 0,
            "code": "01",
            "name": "挂号",
            "business": false,
            "doctor": "",
            "duration": false,
            "process_line_id": 10721,
            "clinic_item": false,
            "is_queue": false,
            "order_num": "",
            "state": "done",
            "wait_minutes": 0,
            "location": "",
            "time_point": "",
            "time": "2017-05-25 09:08",
            "department": "产科专家门诊",
            "queue_state": ""
        },
        {
            "queue_state_code": 4,
            "wait_count": 0,
            "reserve_department_id": 0,
            "code": "02",
            "name": "初诊",
            "business": "就诊",
            "doctor": "",
            "duration": false,
            "process_line_id": 10722,
            "clinic_item": false,
            "is_queue": true,
            "order_num": "",
            "state": "done",
            "wait_minutes": 0,
            "location": false,
            "time_point": "",
            "time": "2017-05-25 09:50",
            "department": "产科门诊",
            "queue_state": "诊结"
        },
        {
            "queue_state_code": 0,
            "wait_count": 0,
            "reserve_department_id": 0,
            "code": "03",
            "name": "缴费",
            "business": false,
            "doctor": "",
            "duration": false,
            "process_line_id": 10949,
            "clinic_item": false,
            "is_queue": false,
            "order_num": "",
            "state": "done",
            "wait_minutes": 0,
            "location": "1楼缴费窗口，1楼自助机",
            "time_point": "",
            "time": "2017-05-25 09:50",
            "department": false,
            "queue_state": ""
        },
        {
            "queue_state_code": -1,
            "wait_count": 0,
            "reserve_department_id": 0,
            "code": "04",
            "name": "检查检验",
            "business": "发药",
            "doctor": "",
            "duration": false,
            "process_line_id": 10984,
            "clinic_item": false,
            "is_queue": true,
            "order_num": "",
            "state": "doing",
            "wait_minutes": 0,
            "location": false,
            "time_point": "",
            "time": "2017-05-25 09:58",
            "department": "西药房",
            "queue_state": "待排队"
        },
        {
            "queue_state_code": -1,
            "wait_count": 0,
            "reserve_department_id": 0,
            "code": "04",
            "name": "检查检验",
            "business": "四维彩超",
            "doctor": "",
            "duration": false,
            "process_line_id": 10985,
            "clinic_item": false,
            "is_queue": true,
            "order_num": "",
            "state": "doing",
            "wait_minutes": 0,
            "location": false,
            "time_point": "",
            "time": "2017-05-25 09:58",
            "department": "B超室",
            "queue_state": "待排队"
        },
        {
            "queue_state_code": -1,
            "wait_count": 0,
            "reserve_department_id": 0,
            "code": "04",
            "name": "检查检验",
            "business": "验血",
            "doctor": "",
            "duration": false,
            "process_line_id": 10983,
            "clinic_item": false,
            "is_queue": true,
            "order_num": "",
            "state": "doing",
            "wait_minutes": 0,
            "location": false,
            "time_point": "",
            "time": "2017-05-25 09:58",
            "department": "检验科",
            "queue_state": "待排队"
        },
        {
            "queue_state_code": 0,
            "wait_count": 0,
            "reserve_department_id": 0,
            "code": "03",
            "name": "缴费",
            "business": false,
            "doctor": "",
            "duration": false,
            "process_line_id": 11134,
            "clinic_item": false,
            "is_queue": false,
            "order_num": "",
            "state": "doing",
            "wait_minutes": 0,
            "location": "1楼缴费窗口，1楼自助机",
            "time_point": "",
            "time": "2017-05-25 10:35",
            "department": false,
            "queue_state": ""
        }
    ]
}

'''