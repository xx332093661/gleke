# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PartnerRelationship(models.Model):
    _name = 'his.partner_relationship'
    _description = u'客户关系'

    parent_id = fields.Many2one('res.partner', '关系人')
    partner_id = fields.Many2one('res.partner', '联系人')
    relationship = fields.Selection([('self', '本人'), ('child', '子女'), ('parents', '父母'), ('husband-wife', '夫妻'), ('friend', '朋友'), ('other', '其他')], '关系')

    @api.onchange('relationship')
    def onchange_relationship(self):
        if self.relationship == 'self' and self._context.get('relation_parent_id'):
            self.partner_id = self._context['relation_parent_id']

    @api.model
    def create(self, vals):
        if vals.get('relationship') == 'self':
            if self.search([('parent_id', '=', vals['parent_id']), ('relationship', '=', 'self')]):
                raise UserError('您只能创建唯一本人！')
        # 每个联系人只能添加一次
        if self.search([('parent_id', '=', vals['parent_id']), ('partner_id', '=', vals['partner_id'])]):
            raise UserError('同一个人只能添加一次！')
        return super(PartnerRelationship, self).create(vals)
