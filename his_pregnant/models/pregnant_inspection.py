# -*- encoding:utf-8 -*-
from datetime import datetime

from odoo import fields, models, api
from odoo.exceptions import Warning
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class PregnantInspection(models.Model):
    _name = 'his.pregnant_inspection'
    _description = '产检计划'
    _order = 'number'
    update_external = True  # 更新外部服务器数据

    @api.model
    def _default_get_number(self):
        pregnant_inspection = self.search([], order='number desc', limit=1)
        if pregnant_inspection:
            return pregnant_inspection.number + 1

        return 1


    @api.model
    def _default_get_start_cycle_id(self):
        pregnant_cycle_obj = self.env['his.pregnant_cycle']

        pregnant_inspection = self.search([], order='number desc', limit=1)
        if pregnant_inspection:
            pregnant_cycle = pregnant_cycle_obj.search([('value', '>', pregnant_inspection.end_cycle_id.value)], order='value asc', limit=1)
            if pregnant_cycle:
                return pregnant_cycle.id

        else:
            pregnant_cycle = pregnant_cycle_obj.search([('value', '>=', 9)], order='value asc', limit=1)
            if pregnant_cycle:
                return pregnant_cycle.id


    start_cycle_id = fields.Many2one('his.pregnant_cycle', '开始孕周', default=_default_get_start_cycle_id)
    end_cycle_id = fields.Many2one('his.pregnant_cycle', '截止孕周')
    main_point = fields.Text('产检重点')
    purpose = fields.Text('产检目的')
    preparation = fields.Text('产检准备')
    precautions = fields.Text('注意事项', help='温馨提示')
    item_ids = fields.Many2many('his.pregnant_inspection_item', 'his_pregnant_inspection_item_rel', 'inspection_id', 'item_id', '检查项目')
    number = fields.Integer('次数', default=_default_get_number)
    number_label = fields.Char('检查顺序', compute='_compute_number_label')

    _sql_constraints = [
        ('number_uniq', 'unique (number)', '检查顺序重复')
    ]

    @api.multi
    def name_get(self):
        res = []
        for pregnant_inspection in self:
            if pregnant_inspection.start_cycle_id.value == pregnant_inspection.end_cycle_id.value:
                name = '孕%d周' % pregnant_inspection.start_cycle_id.value
            else:
                name = '孕%d周-%d周' % (pregnant_inspection.start_cycle_id.value, pregnant_inspection.end_cycle_id.value)
            res += [(pregnant_inspection.id, name)]
        return res


    @api.model
    def _compute_number_label(self):
        for record in self:
            record.number_label = u'第%s次产检' % record.number


    @api.onchange('start_cycle_id')
    def onchange_start_cycle_id(self):
        if self.start_cycle_id:
            return {'domain': {'end_cycle_id': [('value', '>=', self.start_cycle_id.value)]}}

        return {'domain': {'end_cycle_id': []}}


    @api.model
    def create(self, vals):
        pregnant_cycle_obj = self.env['his.pregnant_cycle'] # 产检周期
        pregnant_personal_schedule_obj = self.env['his.pregnant_personal_schedule']  # 孕妇产检计划
        # 周期交叉
        start_cycle = pregnant_cycle_obj.browse(vals['start_cycle_id'])
        if self.search([('start_cycle_id.value', '<=', start_cycle.value), ('end_cycle_id.value', '>=', start_cycle.value)]):
            raise Warning('开始孕周交叉')

        end_cycle = pregnant_cycle_obj.browse(vals['end_cycle_id'])
        if self.search([('start_cycle_id.value', '<=', end_cycle.value), ('end_cycle_id.value', '>=', end_cycle.value)]):
            raise Warning('截止孕周交叉')

        result = super(PregnantInspection, self).create(vals)

        # 创建时修改孕妇产检计划
        today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)

        for partner in self.env['res.partner'].search([('patient_property', '=', 'pregnant'), ('pregnant_in_self', '=', True)]):
            # 忽略已生产的孕妇
            if today >= datetime.strptime(partner.plan_born_day, DATE_FORMAT):
                continue

            # 忽略怀孕周数大于截止孕周的孕妇
            pregnant_days = (today - datetime.strptime(partner.last_menstruation_day, DATE_FORMAT)).days  # 怀孕天数
            pregnant_weeks, _ = divmod(pregnant_days, 7)  # 怀孕周数
            if pregnant_weeks >= result.end_cycle_id.value:
                continue

            pregnant_personal_schedule_obj.create({
                'partner_id': partner.id,
                'start_cycle_id': result.start_cycle_id.id,  # 开始孕周
                'end_cycle_id': result.end_cycle_id.id,  # 截止孕周
                'main_point': result.main_point,  # 产检重点
                'purpose': result.purpose,  # 产检目的
                'preparation': result.preparation,  # 产检准备
                'precautions': result.precautions,  # 注意事项
                'number': result.number,  # 检查顺序
                'item_ids': [(6, 0, [item.id for item in result.item_ids])],  # 检查项目
            })

        return result


    @api.multi
    def write(self, vals):
        """修改时修改孕妇产检计划"""
        pregnant_cycle_obj = self.env['his.pregnant_cycle']  # 产检周期
        pregnant_personal_schedule_obj = self.env['his.pregnant_personal_schedule']  # 孕妇产检计划

        # 周期交叉
        if 'start_cycle_id' in vals:
            start_cycle = pregnant_cycle_obj.browse(vals['start_cycle_id'])
            if self.search([('start_cycle_id.value', '<=', start_cycle.value), ('end_cycle_id.value', '>=', start_cycle.value), ('id', '!=', self.id)]):
                raise Warning('开始孕周交叉')

        if 'end_cycle_id' in vals:
            end_cycle = pregnant_cycle_obj.browse(vals['end_cycle_id'])
            if self.search([('start_cycle_id.value', '<=', end_cycle.value), ('end_cycle_id.value', '>=', end_cycle.value), ('id', '!=', self.id)]):
                raise Warning('截止孕周交叉')


        # 修改时修改孕妇的产检计划
        today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)

        old_number = self.number # 第几次检查

        res = super(PregnantInspection, self).write(vals)

        for partner in self.env['res.partner'].search([('patient_property', '=', 'pregnant'), ('pregnant_in_self', '=', True)]):
            if today >= datetime.strptime(partner.plan_born_day, DATE_FORMAT): # 忽略已生产的孕妇
                continue


            pregnant_personal_schedule = pregnant_personal_schedule_obj.search([('partner_id', '=', partner.id), ('number', '=', old_number)])

            if pregnant_personal_schedule:
                # 忽略已做产检的计划
                if pregnant_personal_schedule.state == '1':
                    continue

                pregnant_personal_schedule.write({
                    'start_cycle_id': self.start_cycle_id.id,  # 开始孕周
                    'end_cycle_id': self.end_cycle_id.id,  # 截止孕周
                    'main_point': self.main_point,  # 产检重点
                    'purpose': self.purpose,  # 产检目的
                    'preparation': self.preparation,  # 产检准备
                    'precautions': self.precautions,  # 注意事项
                    'number': self.number,  # 检查顺序
                    'item_ids': [(6, 0, [item.id for item in self.item_ids])],  # 检查项目
                })
        return res


    def unlink(self):
        pregnant_personal_schedule_obj = self.env['his.pregnant_personal_schedule']  # 孕妇产检计划

        # 删除时修改孕妇产检计划
        today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)

        for partner in self.env['res.partner'].search([('patient_property', '=', 'pregnant'), ('pregnant_in_self', '=', True)]):
            if today >= datetime.strptime(partner.plan_born_day, DATE_FORMAT): # 忽略已生产的孕妇
                continue

            pregnant_personal_schedule = pregnant_personal_schedule_obj.search([('partner_id', '=', partner.id), ('number', '=', self.number)])
            if pregnant_personal_schedule:
                # 忽略已做产检的计划
                if pregnant_personal_schedule.state == '1':
                    continue

                pregnant_personal_schedule.unlink()

        return super(PregnantInspection, self).unlink()



class PregnantInspectionItem(models.Model):
    _name = 'his.pregnant_inspection_item'
    _description = '产检项目'
    update_external = True  # 更新外部服务器数据

    name = fields.Char('项目名称')
    description = fields.Text('项目描述')

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.context.get('schedule_id'):
            if not args:
                args = []

            pregnant_personal_schedule = self.env['his.pregnant_personal_schedule'].browse(self.env.context['schedule_id'])
            args += [('id', 'in', [item.id for item in pregnant_personal_schedule.item_ids])]

        return super(PregnantInspectionItem, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        personal_schedule_obj = self.env['his.pregnant_personal_schedule'] # 孕妇产检计划
        mother_inspection_detail_obj = self.env['his.mother_inspection_detail'] # 孕妇产检明细记录

        if not args:
            args = []

        if self.env.context.get('schedule_id'):
            personal_schedule = personal_schedule_obj.browse(self.env.context.get('schedule_id'))
            all_item_ids = [item.id for item in personal_schedule.item_ids]

            exist_item_ids = []
            for detail in self.env.context['detail_ids']:
                if detail[0] == 0:
                    exist_item_ids.append(detail[2]['item_id'])
                if detail[0] == 4:
                    mother_inspection_detail = mother_inspection_detail_obj.browse(detail[0])
                    exist_item_ids.append(mother_inspection_detail.item_id.id)

            ids = list(set(all_item_ids) - set(exist_item_ids))
            args += [('id', 'in', ids)]


        return super(PregnantInspectionItem, self).name_search(name=name, args=args, operator=operator, limit=limit)













