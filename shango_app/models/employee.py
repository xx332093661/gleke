# -*- encoding:utf-8 -*-
from odoo import api
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    introduction = fields.Text('简介')
    his_id = fields.Integer('hisId')
    good_at = fields.Text('擅长')
    title = fields.Char('技术职务')

    internal_id = fields.Integer('内部id')

    @api.model
    def create(self, vals):
        if vals.get('company_id') and vals.get('his_id'):
            obj = self.search([('company_id', '=', vals['company_id']), ('his_id', '=', vals['his_id'])])

            if obj:
                if vals.get('internal_id') and obj.internal_id != vals['internal_id']:
                    obj.internal_id = vals['internal_id']
                return obj
        return super(HrEmployee, self).create(vals)




