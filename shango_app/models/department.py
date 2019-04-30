# -*- encoding:utf-8 -*-
from odoo import api
from odoo import fields, models


class Department(models.Model):
    _inherit = 'hr.department'

    pinyin = fields.Char('拼音')
    internal_id = fields.Integer('内部id')
    his_id = fields.Integer('hisId')
    location = fields.Char('位置')
    image = fields.Binary('图片')

    @api.model
    def create(self, vals):
        if vals.get('company_id') and vals.get('his_id'):
            obj = self.search([('company_id', '=', vals['company_id']), ('his_id', '=', vals['his_id'])])

            if obj:
                if vals.get('internal_id') and obj.internal_id != vals['internal_id']:
                    obj.internal_id = vals['internal_id']
                return obj

        return super(Department, self).create(vals)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        department_id = self.env.context.get('department_id')
        if department_id:
            # 根据科室过滤诊室
            args += [('parent_id', '=', department_id)]

        return super(Department, self).name_search(name, args, operator=operator, limit=limit)

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.parent_id:
                name = "%s / %s" % (record.parent_id.name, name)
            if record.company_id:
                name = '%s / %s' % (record.company_id.name, name)
            result.append((record.id, name))
        return result

