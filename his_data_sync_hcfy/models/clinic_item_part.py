# -*- encoding:utf-8 -*-
from odoo import api
from odoo import models, fields


class ClinicItemPart(models.Model):
    _name = 'his.clinic_item_part'
    _description = '诊疗项目部位'


    his_id = fields.Integer('HISID', index=True)
    name = fields.Char('名称')


    type = fields.Char('类型')
    item_id = fields.Many2one('his.clinic_item_category', '项目ID')


    @api.model
    def his_id_exist(self, his_id):
        return self.search([('his_id', '=', his_id)])


    @api.model
    def create(self, vals):
        res = self.his_id_exist(vals['his_id'])
        if res:
            return res

        return super(ClinicItemPart, self).create(vals)



