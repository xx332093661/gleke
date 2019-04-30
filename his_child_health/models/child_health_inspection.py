# -*- encoding:utf-8 -*-
from odoo import api
from odoo import fields, models


class ChildHealthInspectionItem(models.Model):
    _name = 'his.child_health_inspection_item'
    _description = '儿保项目'
    update_external = True  # 更新外部服务器数据

    image = fields.Binary('图片')
    content = fields.Text('描述')
    name = fields.Char('项目名称')
    product_ids = fields.Many2many('product.template', 'child_health_item_product_template_rel', 'item_id', 'product_id', '产品')
    item_price = fields.Float('项目收费', compute='_compute_item_price')


    @api.multi
    def _compute_item_price(self):
        for record in self:
            record.item_price = sum([product.list_price for product in record.product_ids])


    @api.onchange('product_ids')
    def onchange_product_ids(self):
        self.item_price = sum([product.list_price for product in self.product_ids])


    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        child_inspection_record_detail_obj = self.env['his.child_inspection_record_detail']
        if self.env.context.get('detail_ids'):
            exist = []
            for line in self.env.context['detail_ids']:
                if line[0] == 4:
                    exist.append(child_inspection_record_detail_obj.browse(line[1]).item_id.id)
                if line[0] == 0:
                    exist.append(line[2]['item_id'])

            if not args:
                args += [('id', 'not in', exist)]

        return super(ChildHealthInspectionItem, self).name_search(name=name, args=args, operator=operator, limit=limit)


    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        child_inspection_record_detail_obj = self.env['his.child_inspection_record_detail']
        if self.env.context.get('detail_ids'):
            exist = []
            for line in self.env.context['detail_ids']:
                if line[0] == 4:
                    exist.append(child_inspection_record_detail_obj.browse(line[1]).item_id.id)
                if line[0] == 0:
                    exist.append(line[2]['item_id'])

            if not args:
                args += [('id', 'not in', exist)]
        return super(ChildHealthInspectionItem, self).search(args, offset=offset, limit=limit, order=order, count=count)



class ChildHealthInspection(models.Model):
    _name = 'his.child_health_inspection'
    _description = '儿保计划'
    _order = 'month'
    _rec_name = 'month_label'
    update_external = True  # 更新外部服务器数据

    @api.model
    def _default_get_month(self):
        child_health_cycle_obj = self.env['his.child_health_cycle'] # 儿保周期
        res = self.search([], order='month desc', limit=1)
        if res:
            cycle = child_health_cycle_obj.search([('month', '>', res.month)], order='month asc', limit=1)
            if cycle:
                return cycle.month

            return res.month + 1

        cycle = child_health_cycle_obj.search([], order='month asc', limit=1)
        if cycle:
            return cycle.month

        return 1

    month = fields.Integer('月龄', default=_default_get_month)
    month_label = fields.Char('月龄', compute='_compute_month_label')
    main_point = fields.Text('检查重点')
    item_ids = fields.Many2many('his.child_health_inspection_item', 'child_health_inspection_item_rel', 'inspection_id', 'item_id', '检查项目')

    _sql_constraints = [
        ('month_uniq', 'unique (month)', '月龄重复'),
        ('max_month_value', 'CHECK (month<=36)', '儿保的最大月龄为36个月!'),
    ]


    @api.multi
    def _compute_month_label(self):
        for record in self:
            record.month_label = u'第%d月' % record.month

    @api.model
    def create(self, vals):
        child_health_schedule_obj = self.env['his.child_health_schedule'] # 儿保个人计划

        result = super(ChildHealthInspection, self).create(vals)
        # 创建时创建儿童个人儿保计划
        for partner in self.env['res.partner'].search([('patient_property', '=', 'newborn'), ('child_health_in_self', '=', True)]):
            # 忽略过了儿保年龄段的儿童
            ages = partner.compute_newborn_age(partner.birth_date)  # 计算新生儿年龄
            months = ages.years * 12 + ages.months  # 出生到现在月数
            if months >= 36 or months >= result.month:
                continue

            child_health_schedule_obj.create({
                'partner_id': partner.id,  # 儿童
                'month': result.month,  # 月龄
                'main_point': result.main_point,  # 检查重占
                'item_ids': [(6, 0, [item.id for item in result.item_ids])],
            })

        return result

    @api.multi
    def write(self, vals):
        child_health_schedule_obj = self.env['his.child_health_schedule'] # 儿保个人计划

        old_month = self.month # 原月龄

        res = super(ChildHealthInspection, self).write(vals)

        # 修改时修改儿童个人儿保计划
        for partner in self.env['res.partner'].search([('patient_property', '=', 'newborn'), ('child_health_in_self', '=', True)]):
            ages = partner.compute_newborn_age(partner.birth_date)  # 计算新生儿年龄
            months = ages.years * 12 + ages.months  # 出生到现在月数
            if months >= 36:
                continue

            # 忽略已完成的计划
            child_health_schedule = child_health_schedule_obj.search([('partner_id', '=', partner.id), ('month', '=', old_month)]) # 儿保个人计划
            if child_health_schedule.state == '1':
                continue

            child_health_schedule.write({
                'month': self.month,  # 月龄
                'main_point': self.main_point,  # 检查重占
                'item_ids': [(6, 0, [item.id for item in self.item_ids])],
            })

        return res

    @api.multi
    def unlink(self):
        child_health_schedule_obj = self.env['his.child_health_schedule']  # 儿保个人计划

        for record in self:
            for partner in self.env['res.partner'].search([('patient_property', '=', 'newborn'), ('child_health_in_self', '=', True)]):
                ages = partner.compute_newborn_age(partner.birth_date)  # 计算新生儿年龄
                months = ages.years * 12 + ages.months  # 出生到现在月数
                if months >= 36:
                    continue

                # 忽略已完成的计划
                child_health_schedule = child_health_schedule_obj.search([('partner_id', '=', partner.id), ('month', '=', record.month)]) # 儿保个人计划
                if child_health_schedule.state == '1':
                    continue

                child_health_schedule.unlink()

        return super(ChildHealthInspection, self).unlink()





















