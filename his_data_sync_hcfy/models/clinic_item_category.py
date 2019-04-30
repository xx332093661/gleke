# -*- encoding:utf-8 -*-
from odoo import api
from odoo import models, fields


class ClinicItemCategory(models.Model):
    _name = 'his.clinic_item_category'
    _description = '诊疗项目目录'


    his_id = fields.Integer('HISID', index=True)
    code = fields.Char('编码')
    name = fields.Char('名称')

    unit = fields.Char('计算单位')
    type = fields.Char('类别')
    category_id = fields.Many2one('his.clinic_classification_category', '分类ID')
    business_id = fields.Many2one('hrp.business', '业务类别')


    @api.model
    def his_id_exist(self, his_id):
        return self.search([('his_id', '=', his_id)])


    @api.model
    def create(self, vals):
        res = self.his_id_exist(vals['his_id'])
        if res:
            return res

        return super(ClinicItemCategory, self).create(vals)
