# -*- encoding:utf-8 -*-
import json
import logging
from functools import wraps

from odoo import api
from odoo import models

_logger = logging.getLogger(__name__)


class ComputeRelationException(Exception):
    pass



def crud_wraps(func):
    """增删改查方法包装"""
    @wraps(func)
    def wrapper(self, message):
        company_id = False
        company = self.env['res.company'].search([('topic', '=', message.source_topic)])
        if company:
            company_id = company.id

        return func(self, company_id, message)

    return wrapper



class EmqttBusinessProcess(models.TransientModel):
    """Emqtt业务处理"""
    _inherit = 'shango.emqtt'

    def get_relation_id(self, model, internal_id, company_id=None):
        """返回关系字段的"""
        if model == 'res.partner':
            return internal_id

        if not internal_id:
            return False

        obj = self.env[model]
        if hasattr(obj, 'internal_id'):
            res = obj.search([('company_id', '=', company_id), ('internal_id', '=', internal_id)])
            if res:
                return res.id

            _logger.error(u'不能找到医院%d的%s对应的内部ID:%d', company_id, model, internal_id)
            raise ComputeRelationException

        return None


    @api.model
    @crud_wraps
    def create(self, company_id, message):
        """基础数据创建"""

        data = json.loads(message.payload)
        vals = {}

        obj = self.env[data['model']]

        for field_name, field_val in data['vals'].items():
            if field_name == 'company_id':
                continue

            if not obj._fields.get(field_name):
                continue

            field_type = obj._fields[field_name].type # 字段类型

            if field_type == 'many2one':
                vals[field_name] = self.get_relation_id(field_val['model'], field_val['id'], company_id)
            elif field_type == 'many2many':
                ids = field_val['id'][0].pop(2)
                res = self.env[field_val['model']].sudo().search([('company_id', '=', company_id), ('internal_id', 'in', ids)])
                ids = [r.id for r in res]
                field_val['id'][0].append(ids)
                vals[field_name] = field_val['id']
            else:
                vals[field_name] = field_val

        vals['company_id'] = company_id
        obj.create(vals)


    @api.model
    @crud_wraps
    def write(self, company_id, message):
        """基础数据修改"""
        data = json.loads(message.payload)

        model = data.pop('model')
        obj = self.env[model].sudo()

        # 公司处理
        if model == 'res.company':
            vals = {}

            for field_name, field_val in data['vals'].items():
                if not obj._fields.get(field_name):
                    continue

                field_type = obj._fields[field_name].type

                if field_type == 'many2one':
                    vals[field_name] = self.get_relation_id(field_val['model'], field_val['id'], company_id)
                elif field_type == 'many2many':
                    ids = field_val['id'][0].pop(2)
                    res = self.env[field_val['model']].sudo().search(
                        [('company_id', '=', company_id), ('internal_id', 'in', ids)])
                    ids = [r.id for r in res]
                    field_val['id'][0].append(ids)
                    vals[field_name] = field_val['id']
                else:
                    vals[field_name] = field_val

            if vals:
                obj.browse(company_id).write(vals)
        else:
            vals = {}
            internal_id = data['vals'].pop('internal_id') # 内部ID


            for field_name, field_val in data['vals'].items():
                if not obj._fields.get(field_name):
                    continue

                field_type = obj._fields[field_name].type

                if field_type == 'many2one':
                    vals[field_name] = self.get_relation_id(field_val['model'], field_val['id'], company_id)
                elif field_type == 'many2many':
                    ids = field_val['id'][0].pop(2)
                    res = self.env[field_val['model']].sudo().search([('company_id', '=', company_id), ('internal_id', 'in', ids)])
                    ids = [r.id for r in res]
                    field_val['id'][0].append(ids)
                    vals[field_name] = field_val['id']
                else:
                    vals[field_name] = field_val

            if vals:
                obj.search([('company_id', '=', company_id), ('internal_id', '=', internal_id)]).write(vals)


    @api.model
    @crud_wraps
    def unlink(self, company_id, message):
        """基础数据删除"""
        data = json.loads(message.payload)
        res = self.env[data['model']].sudo().search([('company_id', '=', company_id), ('internal_id', 'in', data['vals']['internal_id'])])
        if res:
            res.unlink()
        else:
            _logger.error(u'处理MQTT删除出错，%s对应的外部数据不存在!' % message.id)
