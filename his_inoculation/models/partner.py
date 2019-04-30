# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import api
from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.exceptions import Warning


class Partner(models.Model):
    _inherit = 'res.partner'

    inoculation_code = fields.Char('儿童编码')
    note_code = fields.Char('接种本条形码')
    inoculation_in_self = fields.Boolean('在本院接种')
    inoculation_personal_schedule_ids = fields.One2many('his.inoculation_personal_schedule', 'partner_id', '个人接种计划')
    inoculation_record_ids = fields.One2many('his.inoculation_record', 'partner_id', '接种记录')


    @api.model
    def create(self, vals):
        inoculation_schedule_obj = self.env['his.inoculation_schedule'] # 接种计划
        personal_schedule_obj = self.env['his.inoculation_personal_schedule'] # 个人接种计划
        personal_schedule_detail_obj = self.env['his.inoculation_personal_schedule_detail']  # 新生儿接种计划明细
        inoculation_register_obj = self.env['his.inoculation_register'] # 接种登记

        # 计算接种登记医院
        if vals.get('patient_property') == 'newborn':  # 新生儿
            today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)
            if datetime.strptime(vals['birth_date'], DATE_FORMAT) > today:
                raise Warning('出生日期不能大于当前日期')

            if self.env.context.get('patient_property') == 'newborn': # 在视图中创建
                vals['inoculation_in_self'] = True  # 在本院接种
            else: # 通过接口创建
                inoculation_register = inoculation_register_obj.search([('code', '=', vals['inoculation_code'])])
                if inoculation_register:
                    vals['inoculation_in_self'] = True # 在本院接种
                else:
                    inoculation_register = inoculation_register_obj.search([('note_code', '=', vals['note_code'])])
                    if inoculation_register:
                        vals['inoculation_in_self'] = True # 在本院接种

        partner = super(Partner, self).create(vals)

        # 新生儿创建接种计划
        if partner.patient_property == 'newborn':  # 新生儿
            if partner.inoculation_in_self: # 在本院结种
                ages = self.compute_newborn_age(partner.birth_date)  # 计算新生儿年龄
                months = ages.years * 12 + ages.months  # 出生到现在月数

                for schedule in inoculation_schedule_obj.search([('cycle_id.value', '>=', months)]):
                    personal_schedule = personal_schedule_obj.create({
                        'partner_id': partner.id,
                        'cycle_id': schedule.cycle_id.id, # 接种周期
                    })
                    for detail in schedule.detail_ids:
                        personal_schedule_detail_obj.create({
                            'schedule_id': personal_schedule.id,
                            'item_id': detail.item_id.id,
                            'agent_count': detail.agent_count,
                            'necessary': detail.necessary
                        })

        return partner


    @api.multi
    def write(self, vals):
        inoculation_schedule_obj = self.env['his.inoculation_schedule'] # 接种计划
        personal_schedule_obj = self.env['his.inoculation_personal_schedule'] # 个人接种计划
        personal_schedule_detail_obj = self.env['his.inoculation_personal_schedule_detail']  # 新生儿接种计划明细
        inoculation_register_obj = self.env['his.inoculation_register'] # 接种登记

        if self.patient_property == 'newborn' or vals.get('patient_property') == 'newborn':
            if 'birth_date' in vals:
                today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)
                if datetime.strptime(vals['birth_date'], DATE_FORMAT) > today:
                    raise Warning('出生日期不能大于当前日期')

            if 'inoculation_code' in vals and self.inoculation_code != vals['inoculation_code']: # 修改儿童编码
                inoculation_register = inoculation_register_obj.search([('code', '=', vals['inoculation_code'])])
                if inoculation_register:
                    vals['inoculation_in_self'] = True  # 在本院接种
                else:
                    if self.inoculation_in_self:
                        vals['inoculation_in_self'] = False
            else:
                if 'note_code' in vals and self.note_code != vals['note_code']: # 修改接种本条形码
                    inoculation_register = inoculation_register_obj.search([('note_code', '=', vals['note_code'])])
                    if inoculation_register:
                        vals['inoculation_in_self'] = True  # 在本院接种
                    else:
                        if self.inoculation_in_self:
                            vals['inoculation_in_self'] = False

        result = super(Partner, self).write(vals)
        if self.patient_property != 'newborn':
            return result

        # 生成新的接种计划
        if 'birth_date' in vals or 'inoculation_in_self' in vals: # 修改出生日期 修改是否在本院接种
            personal_schedule_obj.search([('partner_id', '=', self.id)]).unlink() # 删除原有计划

            if self.inoculation_in_self:
                ages = self.compute_newborn_age(self.birth_date)  # 计算新生儿年龄
                months = ages.years * 12 + ages.months  # 出生到现在月数

                for schedule in inoculation_schedule_obj.search([('cycle_id.value', '>=', months)]):
                    personal_schedule = personal_schedule_obj.create({
                        'partner_id': self.id,
                        'cycle_id': schedule.cycle_id.id, # 接种周期
                    })
                    for detail in schedule.detail_ids:
                        personal_schedule_detail_obj.create({
                            'schedule_id': personal_schedule.id,
                            'item_id': detail.item_id.id,
                            'agent_count': detail.agent_count,
                            'necessary': detail.necessary
                        })

        return result





