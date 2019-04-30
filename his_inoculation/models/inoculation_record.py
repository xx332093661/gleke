# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.exceptions import Warning


class InoculationRecord(models.Model):
    _name = 'his.inoculation_record'
    _description = '接种记录'
    _rec_name = 'schedule_id'
    update_external = True  # 更新外部服务器数据

    partner_id = fields.Many2one('res.partner', '接种儿童', ondelete='cascade')
    schedule_id = fields.Many2one('his.inoculation_personal_schedule', '接种计划', ondelete='cascade')
    age = fields.Char('接种年龄', compute='_compute_age')
    inoculate_time = fields.Date('接种日期', default=lambda x: datetime.now().strftime(DATE_FORMAT))
    doctor = fields.Char('接种医生')
    detail_ids = fields.One2many('his.inoculation_record_detail', 'record_id', '记录明细')


    @api.model
    def create(self, val):
        cycle_obj = self.env['his.inoculation_cycle'] # 接种周期
        schedule_obj = self.env['his.inoculation_personal_schedule'] # 新生儿接种计划
        schedule_detail_obj = self.env['his.inoculation_personal_schedule_detail'] # 新生儿接种计划明细

        record = super(InoculationRecord, self).create(val)
        record.schedule_id.state = '1' # 更改接种记录对应的接种计划的状态

        # 未接种的明细
        no_inoculation_detail = []

        for detail in record.schedule_id.detail_ids: # 接种计划必须打的
            if not detail.necessary:
                continue

            exist = False # 已接种
            for record_detail in record.detail_ids: # 接种记录明细
                if detail.item_id.id == record_detail.item_id.id and detail.agent_count == record_detail.agent_count:
                    exist = True

            if not exist: # 未接种
                no_inoculation_detail.append(detail)

        if no_inoculation_detail:
            cycle = cycle_obj.search([('value', '=', record.schedule_id.cycle_id.value + 1)])
            if cycle:
                personal_schedule = schedule_obj.search([('partner_id', '=', record.partner_id.id), ('cycle_id.value', '=', record.schedule_id.cycle_id.value + 1)], limit=1) # 下个月接种计划
                if not personal_schedule:
                    personal_schedule = schedule_obj.create({
                        'partner_id': record.partner_id.id,
                        'cycle_id': cycle.id,
                    })
                    for detail in no_inoculation_detail:
                        schedule_detail_obj.create({
                            'schedule_id': personal_schedule.id,
                            'item_id': detail.item_id.id,
                            'agent_count': detail.agent_count,
                            'necessary': detail.necessary,
                            'is_private': detail.is_private,
                            'source_schedule_id': detail.source_schedule_id.id if detail.source_schedule_id else record.schedule_id.id
                        })
                else:
                    for detail in no_inoculation_detail:
                        schedule_detail_obj.create({
                            'schedule_id': personal_schedule.id,
                            'item_id': detail.item_id.id,
                            'agent_count': detail.agent_count,
                            'necessary': detail.necessary,
                            'is_private': detail.is_private,
                            'source_schedule_id': detail.source_schedule_id.id if detail.source_schedule_id else record.schedule_id.id
                        })

        return record

    @api.multi
    def unlink(self):
        for record in self:
            record.schedule_id.state = '0'
        return super(InoculationRecord, self).unlink()


    @staticmethod
    def compute_newborn_age(birthday, inoculate_time):
        """计算新生儿年龄"""
        inoculate_time = datetime.strptime(inoculate_time, DATE_FORMAT)  # 当前日期
        birthday = datetime.strptime(birthday, DATE_FORMAT)  # 出生日期
        ages = relativedelta(inoculate_time, birthday)  # 新生儿年龄
        return ages


    @api.multi
    def _compute_age(self):
        for record in self:
            if not record.partner_id.birth_date or not record.inoculate_time:
                continue

            ages = self.compute_newborn_age(record.partner_id.birth_date, record.inoculate_time)  # 计算新生儿年龄
            months = ages.years * 12 + ages.months  # 出生到现在月数
            if not months:
                record.age = '%d天' % ages.days
            elif not ages.years:
                record.age = '%d个月+%d天' % (ages.months, ages.days) if ages.days else '%d个月' % ages.months
            else:
                if ages.years >= 7:
                    record.age = '%d周岁' % ages.years
                else:
                    if not ages.months:
                        record.age = '%d周岁' % ages.years
                    elif ages.months == 6:
                        record.age = '%d岁半' % ages.years
                    else:
                        record.age = '%d岁%d个月' % (ages.years, ages.months)


    @api.onchange('partner_id', 'inoculate_time')
    def onchange_partner_id(self):
        personal_schedule_obj = self.env['his.inoculation_personal_schedule']  # 个人接种计划

        if self.inoculate_time:
            today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)
            if datetime.strptime(self.inoculate_time, DATE_FORMAT) > today:
                raise Warning('检查日期不能大于当前日期!')


        if not self.partner_id or not self.inoculate_time:
            age = False
            domain = []
        else:
            ages = self.compute_newborn_age(self.partner_id.birth_date, self.inoculate_time)  # 计算新生儿年龄
            months = ages.years * 12 + ages.months  # 出生到现在月数
            if not months:
                age = '%d天' % ages.days
            elif not ages.years:
                age = '%d个月+%d天' % (ages.months, ages.days) if ages.days else '%d个月' % ages.months
            else:
                if ages.years >= 7:
                    age = '%d周岁' % ages.years
                else:
                    if not ages.months:
                        age = '%d周岁' % ages.years
                    elif ages.months == 6:
                        age = '%d岁半' % ages.years
                    else:
                        age = '%d岁%d个月' % (ages.years, ages.months)

            personal_schedule = personal_schedule_obj.search([('partner_id', '=', self.partner_id.id), ('cycle_id.value', '<=', months), ('state', '=', '0')])
            domain = [('id', 'in', [schedule.id for schedule in personal_schedule])]
        return {
            'value': {'age': age},
            'domain': {'schedule_id': domain}
        }


class InoculationRecordDetail(models.Model):
    _name = 'his.inoculation_record_detail'
    _description = '接种记录明细'
    update_external = True  # 更新外部服务器数据

    record_id = fields.Many2one('his.inoculation_record', '接种记录', ondelete='cascade')
    item_id = fields.Many2one('his.inoculation_item', '接种项目', ondelete='cascade')
    agent_count = fields.Selection([(1, '第一剂'), (2, '第二剂'), (3, '第三剂'), (4, '第四剂'), (5, '第五剂'), (6, '第六剂')], '剂数')

    batch_number = fields.Char('批次号')
    vaccine_manufacturer = fields.Char('疫苗厂商')

    @api.onchange('item_id')
    def onchange_item_id(self):
        personal_schedule_detail_obj = self.env['his.inoculation_personal_schedule_detail'] # 新生儿接种计划明细
        if not self.item_id:
            self.agent_count = 1
        else:
            personal_schedule_detail = personal_schedule_detail_obj.search([('schedule_id', '=', self.env.context['schedule_id']), ('item_id', '=', self.item_id.id)], order='agent_count asc', limit=1)
            self.agent_count = personal_schedule_detail.agent_count

