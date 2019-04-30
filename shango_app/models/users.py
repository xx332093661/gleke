# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Users(models.Model):
    _inherit = 'res.users'

    origin = fields.Selection([('odoo', 'ODOO'), ('add_user', '维护添加'), ('app', '手机')], '来源', default='odoo')

    @api.model
    def default_get(self, fields_list):
        res = super(Users, self).default_get(fields_list)
        if self._context.get('add_user'):
            res.update({'origin': 'add_user'})
        return res

    @api.model
    def create(self, vals):
        if vals.get('origin') == 'add_user':
            vals.update({
                # 'password': '123456',
                'groups_id': [(6, 0, [])]
            })
        return super(Users, self).create(vals)

    @api.multi
    def write(self, vals):
        # 修改partner密码
        for user in self:
            if 'password' in vals:
                user.partner_id.password = vals['password']
        return super(Users, self).write(vals)
