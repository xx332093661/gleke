# -*- encoding:utf-8 -*-
import json
import logging
from datetime import datetime, timedelta

import xmltodict

from odoo import models, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


_logger = logging.getLogger(__name__)


class Department(models.Model):
    _inherit = 'hr.department'
    update_external = True  # 更新外部服务器数据

    @api.model
    def sync_register_plan(self):
        """同步挂号安排"""

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

        department_obj = self.env['hr.department'] # 科室
        department_employee_obj = self.env['his.schedule_department_employee'] # 科室排班人员
        interface_obj = self.env['his.interface'] # his接口
        shift_type_default_obj = self.env['his.shift_type_default'] # 默认班次
        shift_type_obj = self.env['his.shift_type'] # 科室班次

        today = (datetime.now() + timedelta(days=0)).strftime(DATE_FORMAT) # 当前日期
        shift_type_defaults = shift_type_default_obj.search([]) # 默认班次

        register_type_names = interface_obj.get_register_type() # 得到号类

        # 所有挂号科室
        department_ids = [] # 所有挂号科室
        for register_type_name in register_type_names:
            try:
                department_ids += interface_obj.get_department(today, register_type_name)  # 查询能挂的科室列表
            except:
                _logger.info(u'查询%s号类的挂号科室出错', register_type_name)
                # TODO 测试
                if register_type_name == u'专家':
                    from_his_xml = """<?xml version="1.0" encoding="utf-8" ?>
    <Response>
        <TransCode>4002</TransCode>
        <ResultCode>0</ResultCode>
        <ErrorMsg></ErrorMsg>
        <Count>5</Count>
        <ReturnQty>5</ReturnQty>
        <List>
            <Item>
                <DeptID>822</DeptID>
                <DeptCode>1022</DeptCode>
                <DeptName>产科专家门诊</DeptName>
            </Item>
            <Item>
                <DeptID>346</DeptID>
                <DeptCode>1122</DeptCode>
                <DeptName>妇科专家门诊</DeptName>
            </Item>
            <Item>
                <DeptID>348</DeptID>
                <DeptCode>1124</DeptCode>
                <DeptName>急诊妇科专家门诊</DeptName>
            </Item>
            <Item>
                <DeptID>823</DeptID>
                <DeptCode>1231</DeptCode>
                <DeptName>儿科专家门诊</DeptName>
            </Item>
            <Item>
                <DeptID>862</DeptID>
                <DeptCode>1234</DeptCode>
                <DeptName>急诊儿科专家门诊</DeptName>
            </Item>
        </List>
    </Response>
                    """
                else:
                    from_his_xml = """<?xml version="1.0" encoding="utf-8" ?>
<Response>
    <TransCode>4002</TransCode>
    <ResultCode>0</ResultCode>
    <ErrorMsg></ErrorMsg>
    <Count>8</Count>
    <ReturnQty>8</ReturnQty>
    <List>
        <Item>
            <DeptID>821</DeptID>
            <DeptCode>1021</DeptCode>
            <DeptName>产科普通门诊</DeptName>
        </Item>
        <Item>
            <DeptID>863</DeptID>
            <DeptCode>1023</DeptCode>
            <DeptName>急诊产科普通门诊</DeptName>
        </Item>
        <Item>
            <DeptID>864</DeptID>
            <DeptCode>1024</DeptCode>
            <DeptName>急诊产科专家门诊</DeptName>
        </Item>
        <Item>
            <DeptID>345</DeptID>
            <DeptCode>1121</DeptCode>
            <DeptName>妇科普通门诊</DeptName>
        </Item>
        <Item>
            <DeptID>347</DeptID>
            <DeptCode>1123</DeptCode>
            <DeptName>急诊妇科普通门诊</DeptName>
        </Item>
        <Item>
            <DeptID>824</DeptID>
            <DeptCode>1232</DeptCode>
            <DeptName>儿科普通门诊</DeptName>
        </Item>
        <Item>
            <DeptID>861</DeptID>
            <DeptCode>1233</DeptCode>
            <DeptName>急诊儿科普通门诊</DeptName>
        </Item>
        <Item>
            <DeptID>361</DeptID>
            <DeptCode>6000</DeptCode>
            <DeptName>外科</DeptName>
        </Item>
    </List>
</Response>
                    """

                his_return_dict = json.loads(json.dumps(xmltodict.parse(from_his_xml, encoding='utf-8')))['Response']
                his_return_dict.pop('TransCode')
                his_return_dict.pop('ResultCode')
                his_return_dict.pop('ErrorMsg')

                his_return_convert(his_return_dict)
                # _logger.info(json.dumps(his_return_dict, ensure_ascii=False, encoding='utf8', indent=4))
                get_department_id = lambda his_id: department_obj.search([('his_id', '=', his_id)]).id
                departments = his_return_dict['List']['Item']
                if isinstance(departments, dict):
                    departments = [departments]

                department_ids += [get_department_id(department['DeptID']) for department in departments]



        department_ids = list(set(department_ids)) # 所有挂号科室消重
        _logger.info(json.dumps(department_ids, ensure_ascii=False, encoding='utf-8', indent=4))

        current_plan_department_ids = [department.id for department in department_obj.search([('is_shift', '=', True), ('is_outpatient', '=', True)])] # 当前所有门诊排班科室

        # 更改不参与排班科室的is_shift字段
        for department in department_obj.browse(list(set(current_plan_department_ids) - set(department_ids))):
            department.is_shift = False # 不参与排班

        # 更改未参与排班科室的is_shift字段
        for department in department_obj.browse(list(set(department_ids) - set(current_plan_department_ids))):
            department.write({
                'is_shift': True,
                'is_outpatient': True
            })
            # 创建科室班次
            if not department.shift_type_ids:
                for default in shift_type_defaults:
                    shift_type_obj.create({
                        'name': default.name,
                        'department_id': department.id,
                        'start_time': default.start_time,
                        'end_time': default.end_time,
                        'color': default.color,
                        'label': default.name[0]
                    })


        for department in department_obj.browse(department_ids):
            employees = []
            for register_type_name in register_type_names:
                try:
                    res = interface_obj.get_register_employee(register_type_name, department.his_id)  # 查询能挂的科室医生列表
                    employees += res
                except:
                    pass
            _logger.info('HHHHHHHHHHH')
            _logger.info(employees)

            # 删除不参与排班的医生
            employee_ids = [employee['employee_id'] for employee in employees]
            for department_employee in department.employees:
                if department_employee.employee_id.id not in employee_ids:
                    department_employee.unlink()

            # 添加未参与排班的医生
            for employee in employees:
                exist = False
                for department_employee in department.employees:
                    if department_employee.employee_id.id == employee['employee_id']:
                        exist = True
                        break

                if not exist:
                    department_employee_obj.create({
                        'department_id': department.id,
                        'employee_id': employee['employee_id'],
                        'register_type': employee['register_type'],
                        'as_rowid': employee['as_rowid']
                    })
        #
        #     # 挂号收费处理
        #     for department_employee in department.employees:
        #         old_product_ids = [product.id for product in department_employee.product_ids] # 原来的收费项目
        #         for employee in employees:
        #             if department_employee.employee_id.id == employee['employee_id']:
        #                 new_product_ids = employee['product_ids'] # 新的收费项目
        #                 if list(set(old_product_ids) - set(new_product_ids)) or list(set(new_product_ids) - set(old_product_ids)): # 收费项目发生变动
        #                     department_employee.write({
        #                         'product_ids': [(6, 0, new_product_ids)]
        #                     })


