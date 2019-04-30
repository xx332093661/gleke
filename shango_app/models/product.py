# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    fee_name = fields.Char('收据费目')
    internal_id = fields.Integer('内部id')
    his_id = fields.Integer('hisId')

    @api.model
    def create(self, vals):
        if vals.get('company_id') and vals.get('his_id'):
            obj = self.search([('company_id', '=', vals['company_id']), ('his_id', '=', vals['his_id'])])

            if obj:
                if vals.get('internal_id') and obj.internal_id != vals['internal_id']:
                    obj.internal_id = vals['internal_id']
                return obj
        return super(ProductTemplate, self).create(vals)


class ProductCategory(models.Model):
    _inherit = 'product.category'

    internal_id = fields.Integer('内部id')
    company_id = fields.Many2one('res.company', '公司')

    @api.model
    def create(self, vals):
        if vals.get('company_id') and vals.get('name'):
            obj = self.search([('company_id', '=', vals['company_id']), ('name', '=', vals['name'])])

            if obj:
                if vals.get('internal_id') and obj.internal_id != vals['internal_id']:
                    obj.internal_id = vals['internal_id']
                return obj
        return super(ProductCategory, self).create(vals)


class ProductUomCateg(models.Model):
    _inherit = 'product.uom.categ'

    internal_id = fields.Integer('内部id')
    company_id = fields.Many2one('res.company', '公司')

    @api.model
    def create(self, vals):
        if vals.get('company_id') and vals.get('name'):
            obj = self.search([('company_id', '=', vals['company_id']), ('name', '=', vals['name'])])

            if obj:
                if vals.get('internal_id') and obj.internal_id != vals['internal_id']:
                    obj.internal_id = vals['internal_id']
                return obj
        return super(ProductUomCateg, self).create(vals)


class ProductUom(models.Model):
    _inherit = 'product.uom'

    internal_id = fields.Integer('内部id')
    company_id = fields.Many2one('res.company', '公司')

    @api.model
    def create(self, vals):
        if vals.get('company_id') and vals.get('name'):
            obj = self.search([('company_id', '=', vals['company_id']), ('name', '=', vals['name'])])

            if obj:
                if vals.get('internal_id') and obj.internal_id != vals['internal_id']:
                    obj.internal_id = vals['internal_id']
                return obj
        return super(ProductUom, self).create(vals)