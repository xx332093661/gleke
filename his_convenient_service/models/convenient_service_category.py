# -*- encoding:utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import Warning


class ConvenientServiceCategory(models.Model):
    _name = 'his.convenient_service_category'
    _description = '便民服务分类'
    update_external = True  # 更新外部服务器数据


    name = fields.Char('分类名称')
    code = fields.Char('编码')
    origin_prescription = fields.Boolean('数据来源于医嘱')
    parent_id = fields.Many2one('his.convenient_service_category', '父分类', ondelete='cascade')
    type = fields.Selection([('view', '视图'), ('category', '分类')], '类型', default='category')
    prescription_valid = fields.Integer('医嘱有效期', help='单位：天')

    _sql_constraints = [('name_uniq', 'unique (parent_id, name)', '分类名称已经存在'),]


    @api.onchange('parent_id')
    def onchange_parent_id(self):
        self.origin_prescription = self.parent_id.origin_prescription
        self.code = self.parent_id.code
        if not self.origin_prescription:
            self.prescription_valid = 0


    @api.multi
    @api.depends('name', 'parent_id')
    def name_get(self):
        result = []
        for category in self:
            name = category.parent_id.name + '/' + category.name if category.parent_id else category.name
            result.append((category.id, name))
        return result




