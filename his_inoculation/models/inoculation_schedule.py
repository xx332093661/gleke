# -*- coding: utf-8 -*-
from odoo import api
from odoo import models, fields


class InoculationSchedule(models.Model):
    _name = 'his.inoculation_schedule'
    _description = '接种计划'
    _rec_name = 'cycle_id'
    update_external = True  # 更新外部服务器数据

    @api.model
    def _default_get_cycle_id(self):
        inoculation_cycle_obj = self.env['his.inoculation_cycle']
        schedule = self.search([], order='cycle_id desc', limit=1)
        if schedule:
            cycle = inoculation_cycle_obj.search([('value', '>', schedule.cycle_id.value)], order='value asc', limit=1)
            if cycle:
                return cycle.id

        else:
            cycle = inoculation_cycle_obj.search([], order='value asc', limit=1)
            return cycle.id

    cycle_id = fields.Many2one('his.inoculation_cycle', '接种周期', ondelete='cascade', default=_default_get_cycle_id)
    detail_ids = fields.One2many('his.inoculation_schedule_detail', 'schedule_id', '计划明细')


    _sql_constraints = [
        ('item_id_cycle_id_uniq', 'unique (cycle_id)', '接种周期重复'),
    ]


    # @api.model
    # def create(self, vals):
    #     personal_schedule_obj = self.env['his.inoculation_personal_schedule'] # 个人接种计划
    #     personal_schedule_detail_obj = self.env['his.inoculation_personal_schedule_detail'] # 新生儿接种计划明细
    #
    #     result = super(InoculationSchedule, self).create(vals)
    #
    #     # 创建时创建儿童个人儿保计划
    #     for partner in self.env['res.partner'].search([('patient_property', '=', 'newborn'), ('inoculation_in_self', '=', True)]):
    #         # 忽略过了儿保年龄段的儿童
    #         ages = partner.compute_newborn_age(partner.birth_date)  # 计算新生儿年龄
    #         months = ages.years * 12 + ages.months  # 出生到现在月数
    #         if months > 72 or months > result.cycle_id.value:
    #             continue
    #
    #         personal_schedule = personal_schedule_obj.create({
    #             'partner_id': partner.id,
    #             'cycle_id': result.cycle_id.id,  # 接种周期
    #         })
    #         for detail in result.detail_ids:
    #             personal_schedule_detail_obj.create({
    #                 'schedule_id': personal_schedule.id,
    #                 'item_id': detail.item_id.id,
    #                 'agent_count': detail.agent_count,
    #                 'necessary': detail.necessary
    #             })
    #
    #     return result


    # @api.multi
    # def write(self, vals):
    #     inoculation_personal_schedule_obj = self.env['his.inoculation_personal_schedule']  # 个人接种计划
    #
    #     old_cycle_id = self.cycle_id.id
    #     old_item_id = self.item_id.id
    #
    #     res = super(InoculationSchedule, self).write(vals)
    #
    #     for partner in self.env['res.partner'].search([('patient_property', '=', 'newborn'), ('inoculation_in_self', '=', True)]):
    #         # 忽略过了儿保年龄段的儿童
    #         ages = partner.compute_newborn_age(partner.birth_date)  # 计算新生儿年龄
    #         months = ages.years * 12 + ages.months  # 出生到现在月数
    #         if months >= 72 or months >= self.cycle_id.value:
    #             continue
    #
    #         inoculation_personal_schedule = inoculation_personal_schedule_obj.search([('partner_id', '=', partner.id), ('cycle_id', '=', old_cycle_id), ('item_id', '=', old_item_id)])
    #         if inoculation_personal_schedule:
    #             if inoculation_personal_schedule.state == '1':
    #                 continue
    #
    #             inoculation_personal_schedule.write({
    #                 'item_id': self.item_id.id,  # 接种项目
    #                 'cycle_id': self.cycle_id.id,  # 接种周期
    #                 'agent_count': self.agent_count,  # 剂数
    #                 'necessary': self.necessary,  # 是否必打
    #                 'is_private': self.is_private,  # 是否自费
    #             })
    #
    #     return res


    # @api.multi
    # def unlink(self):
    #     inoculation_personal_schedule_obj = self.env['his.inoculation_personal_schedule']  # 个人接种计划
    #
    #     for partner in self.env['res.partner'].search([('patient_property', '=', 'newborn'), ('inoculation_in_self', '=', True)]):
    #         # 忽略过了儿保年龄段的儿童
    #         ages = partner.compute_newborn_age(partner.birth_date)  # 计算新生儿年龄
    #         months = ages.years * 12 + ages.months  # 出生到现在月数
    #         if months >= 72 or months >= self.cycle_id.value:
    #             continue
    #
    #         inoculation_personal_schedule = inoculation_personal_schedule_obj.search([('partner_id', '=', partner.id), ('cycle_id', '=', self.cycle_id.id), ('item_id', '=', self.item_id.id)])
    #         if inoculation_personal_schedule:
    #             if inoculation_personal_schedule.state == '1':
    #                 continue
    #
    #             inoculation_personal_schedule.unlink()
    #
    #     return super(InoculationSchedule, self).unlink()

class InoculationScheduleDetail(models.Model):
    _name = 'his.inoculation_schedule_detail'
    _description = '接种计划明细'
    update_external = True  # 更新外部服务器数据

    schedule_id = fields.Many2one('his.inoculation_schedule', '接种计划', ondelete='cascade')
    item_id = fields.Many2one('his.inoculation_item', '接种项目', ondelete='cascade')
    agent_count = fields.Selection([(1, '第一剂'), (2, '第二剂'), (3, '第三剂'), (4, '第四剂'), (5, '第五剂'), (6, '第六剂')], '剂数')
    necessary = fields.Boolean('是否必打')
    is_private = fields.Boolean('是否自费', related='item_id.is_private')



class InoculationPersonalSchedule(models.Model):
    _name = 'his.inoculation_personal_schedule'
    _description = '新生儿接种计划'
    _rec_name = 'cycle_id'
    update_external = True  # 更新外部服务器数据

    partner_id = fields.Many2one('res.partner', '接种儿童', ondelete='cascade')
    cycle_id = fields.Many2one('his.inoculation_cycle', '接种周期', ondelete='cascade')
    state = fields.Selection([('0', '未接种'), ('1', '已接种')], '状态', default='0')
    detail_ids = fields.One2many('his.inoculation_personal_schedule_detail', 'schedule_id', '计划明细')

    # reserve_record_id = fields.Many2one('his.reserve_record', '预约记录', ondelete='set null')

    # @api.multi
    # @api.depends('partner_id', 'cycle_id')
    # def name_get(self):
    #     result = []
    #     for record in self:
    #         name = '%s/%s' % (record.partner_id.name, record.cycle_id.name)
    #         result.append((record.id, name))
    #     return result
    #
    #
    # @api.model
    # def name_search(self, name='', args=None, operator='ilike', limit=100):
    #     if self.env.context.get('partner_id'):
    #
    #         ids = [schedule.id for schedule in self.search([('partner_id', '=', self.env.context['partner_id']), ('state', '=', '0')])]
    #
    #         if not args:
    #             args += [('id', 'in', ids)]
    #
    #     return super(InoculationPersonalSchedule, self).name_search(name=name, args=args, operator=operator, limit=limit)



class InoculationPersonalScheduleDetail(models.Model):
    _name = 'his.inoculation_personal_schedule_detail'
    _description = '新生儿接种计划明细'
    update_external = True  # 更新外部服务器数据

    schedule_id = fields.Many2one('his.inoculation_personal_schedule', '新生儿接种计划', ondelete='cascade')
    item_id = fields.Many2one('his.inoculation_item', '接种项目', ondelete='cascade')
    agent_count = fields.Selection([(1, '第一剂'), (2, '第二剂'), (3, '第三剂'), (4, '第四剂'), (5, '第五剂'), (6, '第六剂')], '剂数')
    necessary = fields.Boolean('是否必打')
    is_private = fields.Boolean('是否自费', related='item_id.is_private')
    source_schedule_id = fields.Many2one('his.inoculation_personal_schedule', '原计划')




