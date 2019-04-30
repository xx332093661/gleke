# -*- encoding:utf-8 -*-
from datetime import datetime, timedelta
import logging

from odoo import api
from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class SyncDefine(models.Model):
    _inherit = 'his.sync_define'


    @api.model
    def sync_data_history(self):
        """同步数据标记为历史"""
        register_obj = self.env['his.register']
        outpatient_fee_obj = self.env['his.outpatient_fee']
        dispose_send_obj = self.env['his.dispose_send']
        # drug_dispense_obj = self.env['his.drug_dispense']
        dispose_obj = self.env['his.dispose']

        # today = fields.Date.context_today(self)
        create_date = (datetime.now() - timedelta(days=2)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # 病人挂号记录
        register_obj.search([('create_date', '<', create_date)]).unlink()
        # register_obj.search([('register_date', '<', today), ('is_history', '=', False)]).is_history = True

        # 门诊费用记录
        outpatient_fee_obj.search([('create_date', '<', create_date)]).unlink()
        # outpatient_fee_obj.search([('register_date', '<', today), ('is_history', '=', False)]).is_history = True

        # 病人医嘱发送
        dispose_send_obj.search([('create_date', '<', create_date)]).unlink()
        # dispose_send_obj.search([('send_date', '<', today), ('is_history', '=', False)]).is_history = True

        # 病人医嘱记录
        dispose_obj.search([('create_date', '<', create_date)]).unlink()
        # dispose_obj.search([('dispose_date', '<', today), ('is_history', '=', False)]).is_history = True

        # # 药品收发记录
        # drug_dispense_obj.search([('create_date', '<', create_date)]).unlink()
        # drug_dispense_obj.search([('check_date', '<', today), ('is_history', '=', False)]).is_history = True

        return super(SyncDefine, self).sync_data_history()

