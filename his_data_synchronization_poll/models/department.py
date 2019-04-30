# -*- encoding:utf-8 -*-
from odoo import api
from odoo import models, fields



class Department(models.Model):
    _inherit = 'hr.department'

    def get_his_id(self):

        min_his_id = 0
        for department in self.search([]):
            if department.his_id and department.his_id < min_his_id:
                min_his_id = department.his_id

        min_his_id -= 1
        return min_his_id

    his_id = fields.Integer('HISID', index=True, default=lambda self: self.get_his_id())
    location = fields.Char('位置')

    @api.model
    def his_id_exist(self, his_id):
        return self.search([('his_id', '=', his_id)])

    @api.model
    def code_exist(self, code):
        return self.search([('code', '=', code)])

    @api.model
    def create(self, vals):
        if vals.get('his_id'):
            res = self.his_id_exist(vals['his_id'])
            if res:
                return res


        if vals.get('code'):
            res = self.code_exist(vals['code'])
            if res:
                return res


        return super(Department, self).create(vals)

