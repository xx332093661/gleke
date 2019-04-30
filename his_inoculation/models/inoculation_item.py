# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import Warning


class InoculationItem(models.Model):
    _name = 'his.inoculation_item'
    _description = '接种项目'
    update_external = True  # 更新外部服务器数据

    name = fields.Char('名称')
    short_name = fields.Char('名称简写')
    prevent_disease = fields.Char('预防疾病')
    part = fields.Text('接种部位')
    method = fields.Char('接种方法')
    effect = fields.Text('接种效果')
    taboo = fields.Text('禁忌')
    attention = fields.Text('注意事项')
    reaction = fields.Text('可能反应')
    is_private = fields.Boolean('是否自费')
    times = fields.Integer('接种总剂数', default=1)
    product_ids = fields.Many2many('product.template', 'inoculation_item_product_rel', 'item_id', 'product_id', '产品')
    replace_ids = fields.Many2many('his.inoculation_item', 'inoculation_item_replace_rel', 'item_id', 'replace_id', '替代疫苗')
    replace_ids1 = fields.Many2many('his.inoculation_item', 'inoculation_item_replace_rel', 'replace_id', 'item_id', '被替代疫苗')

    _sql_constraints = [
        ('value_name', 'unique (name)', '疫苗名称重复'),
        ('min_times_value', 'CHECK (times>=1)', '接种总剂数必须大于等于1!'),
    ]

    @api.onchange('name')
    def onchange_name(self):
        """计算short_name"""
        if self.name:
            self.short_name = self.name.replace(u'疫苗', u'')

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.context.get('schedule_id'):
            personal_schedule_obj = self.env['his.inoculation_personal_schedule']  # 个人接种计划
            inoculation_record_detail_obj = self.env['his.inoculation_record_detail'] # 接种记录明细

            personal_schedule = personal_schedule_obj.browse(self.env.context.get('schedule_id'))
            all_item_ids = [detail.item_id.id for detail in personal_schedule.detail_ids]

            exist_item_ids = []
            for detail in self.env.context['detail_ids']:
                if detail[0] == 6:
                    exist_item_ids.append(detail[2]['item_id'])
                if detail[0] == 4:
                    inoculation_record_detail = inoculation_record_detail_obj.browse(detail[0])
                    exist_item_ids.append(inoculation_record_detail.item_id.id)

            ids = list(set(all_item_ids) - set(exist_item_ids))
            args += [('id', 'in', ids)]
        return super(InoculationItem, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []

        if self.env.context.get('schedule_id'):
            personal_schedule_obj = self.env['his.inoculation_personal_schedule']  # 个人接种计划
            inoculation_record_detail_obj = self.env['his.inoculation_record_detail'] # 接种记录明细

            personal_schedule = personal_schedule_obj.browse(self.env.context.get('schedule_id'))
            all_item_ids = [detail.item_id.id for detail in personal_schedule.detail_ids]

            exist_item_ids = []
            for detail in self.env.context['detail_ids']:
                if detail[0] == 0:
                    exist_item_ids.append(detail[2]['item_id'])
                if detail[0] == 4:
                    inoculation_record_detail = inoculation_record_detail_obj.browse(detail[0])
                    exist_item_ids.append(inoculation_record_detail.item_id.id)

            ids = list(set(all_item_ids) - set(exist_item_ids))
            args += [('id', 'in', ids)]
        return super(InoculationItem, self).name_search(name=name, args=args, operator=operator, limit=limit)







