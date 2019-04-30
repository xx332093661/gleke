# -*- coding: utf-8 -*-
from odoo import models, fields
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class HrpVerifyCodeRecord(models.Model):
    _name = 'hrp.verify_code_record'
    _description = '验证码发送记录'

    phone = fields.Char('电话')
    verify_code = fields.Char('验证码')
    # state = fields.Selection([('0', '未验证'), ('1', '已验证')], '状态', default='0')
    send_date = fields.Date('发送日期')
    content = fields.Char('短信内容')
    result = fields.Text('发送短信返回结果')
    success = fields.Boolean('是否发送成功')


    def verify(self, phone, verify_code):
        """验证验证码:5分钟过期"""

        # 修改验证码记录状态
        code_record = self.search([('success', '=', True), ('phone', '=', phone), ('verify_code', '=', verify_code), ('create_date', '>=', (datetime.now() - timedelta(minutes=5)).strftime(DEFAULT_SERVER_DATETIME_FORMAT))])
        if code_record:
            # code_record.write({'state': '1'})
            return True

        return False
