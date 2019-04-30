# -*- encoding:utf-8 -*-
from odoo import api
from odoo import models, fields


class ClinicClassificationCategory(models.Model):
    _name = 'his.clinic_classification_category'
    _description = '诊疗分类目录'

    his_id = fields.Integer('HISID', index=True)
    code = fields.Char('编码')
    name = fields.Char('名称')
    parent_id = fields.Many2one('his.clinic_classification_category', '上级ID')
    child_ids = fields.One2many('his.clinic_classification_category', 'parent_id', '子项')
    clinic_item_ids = fields.One2many('his.clinic_item_category', 'category_id', '诊疗项目目录')

    @api.model
    def his_id_exist(self, his_id):
        return self.search([('his_id', '=', his_id)])

    @api.model
    def create(self, vals):
        res = self.his_id_exist(vals['his_id'])
        if res:
            return res

        return super(ClinicClassificationCategory, self).create(vals)





