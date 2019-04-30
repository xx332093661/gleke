# -*- encoding:utf-8 -*-
from odoo import models
from odoo.addons.his_app_hcfy.his_interface.his_interface import his_interface_wrap


class ConnectTest(models.TransientModel):
    _inherit = 'his.interface'

    @his_interface_wrap('1001')
    def connect_test(self):
        """测试是否HIS连接正常"""
        if getattr(self, 'process_to_his_data'):
            return {}

        his_return_dict = getattr(self, 'process_his_return_data')
        return his_return_dict






