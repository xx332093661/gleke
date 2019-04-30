# -*- encoding:utf-8 -*-
from odoo import api
from odoo import models, fields



class Employee(models.Model):
    _inherit = 'hr.employee'

    def get_his_id(self):

        min_his_id = 0
        for employee in self.search([]):
            if employee.his_id and employee.his_id < min_his_id:
                min_his_id = employee.his_id

        min_his_id -= 1
        return min_his_id


    his_id = fields.Integer('HISID', index=True, default=lambda self: self.get_his_id())
    title = fields.Char('专业技术职务')

    @api.model
    def his_id_exist(self, his_id):
        return self.search([('his_id', '=', his_id)])

    @api.model
    def create(self, vals):
        res = self.his_id_exist(vals['his_id'])
        if res:
            return res

        return super(Employee, self).create(vals)
