# -*- encoding:utf-8 -*-
from datetime import datetime

from odoo import api
from odoo import fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class Partner(models.Model):
    _inherit = 'res.partner'


    # month_label = fields.Char('月龄', compute='_compute_month_label')
    inoculation_code = fields.Char('儿童编码')
    note_code = fields.Char('接种本条形码')
    child_health_in_self = fields.Boolean('在本院做儿保')
    child_inspection_record_ids = fields.One2many('his.child_inspection_record', 'partner_id', '儿保记录')
    child_health_schedule_ids = fields.One2many('his.child_health_schedule', 'partner_id', '儿保计划')




    @api.model
    def create(self, vals):
        """创建儿童的儿保计划
        是新生儿且在本院做儿保，则生成儿保计划
        """
        child_health_inspection_obj = self.env['his.child_health_inspection'].sudo()  # 儿保计划
        child_health_schedule_obj = self.env['his.child_health_schedule'].sudo()  # 个人儿保计划
        inoculation_register_obj = self.env['his.inoculation_register']  # 接种登记

        if vals.get('patient_property') == 'newborn':  # 新生儿
            today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)
            if datetime.strptime(vals['birth_date'], DATE_FORMAT) > today:
                raise Warning('出生日期不能大于当前日期')

            if self.env.context.get('patient_property') == 'newborn': # 在视图中创建
                vals['child_health_in_self'] = True  # 在本院做儿保
            else: # 通过接口创建
                inoculation_register = inoculation_register_obj.search([('code', '=', vals['inoculation_code'])])
                if inoculation_register:
                    vals['child_health_in_self'] = True # 在本院做儿保
                else:
                    inoculation_register = inoculation_register_obj.search([('note_code', '=', vals['note_code'])])
                    if inoculation_register:
                        vals['child_health_in_self'] = True # 在本院做儿保

        partner = super(Partner, self).create(vals)

        if partner.patient_property == 'newborn':
            if partner.child_health_in_self:  # 在本院做儿保
                ages = self.compute_newborn_age(partner.birth_date) # 计算新生儿年龄
                months = ages.years * 12 + ages.months  # 出生到现在月数

                for child_health_inspection in child_health_inspection_obj.search([('month', '>=', months)]):
                    child_health_schedule_obj.create({
                        'partner_id': partner.id, # 儿童
                        'month': child_health_inspection.month, # 月龄
                        'main_point': child_health_inspection.main_point, # 检查重占
                        'item_ids': [(6, 0, [item.id for item in child_health_inspection.item_ids])],
                    })

        return partner


    @api.multi
    def write(self, vals):
        """修改儿童的儿保计划
        新生儿更改出生日期，重新生成其儿保计划
        """
        child_health_schedule_obj = self.env['his.child_health_schedule'].sudo()  # 个人儿保计划
        child_health_inspection_obj = self.env['his.child_health_inspection'].sudo()  # 儿保计划
        inoculation_register_obj = self.env['his.inoculation_register']  # 接种登记

        if self.patient_property == 'newborn' or vals.get('patient_property') == 'newborn':
            if 'birth_date' in vals:
                today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)
                if datetime.strptime(vals['birth_date'], DATE_FORMAT) > today:
                    raise Warning('出生日期不能大于当前日期')

            if 'inoculation_code' in vals and self.inoculation_code != vals['inoculation_code']: # 修改儿童编码
                inoculation_register = inoculation_register_obj.search([('code', '=', vals['inoculation_code'])])
                if inoculation_register:
                    vals['child_health_in_self'] = True  # 在本院做儿保
                else:
                    if self.child_health_in_self:
                        vals['inoculation_in_self'] = False
            else:
                if 'note_code' in vals and self.note_code != vals['note_code']: # 修改接种本条形码
                    inoculation_register = inoculation_register_obj.search([('note_code', '=', vals['note_code'])])
                    if inoculation_register:
                        vals['child_health_in_self'] = True  # 在本院做儿保
                    else:
                        if self.child_health_in_self:
                            vals['child_health_in_self'] = False

        result = super(Partner, self).write(vals)

        if 'birth_date' in vals or 'child_health_in_self' in vals:  # 修改出生日期 修改是否在本院做儿保
            child_health_schedule_obj.search([('partner_id', '=', self.id)]).unlink() # 删除所有儿保计划

            if self.child_health_in_self:
                ages = self.compute_newborn_age(vals['birth_date'])  # 计算新生儿年龄
                months = ages.years * 12 + ages.months  # 出生到现在月数

                # 创建新的儿保计划
                for child_health_inspection in child_health_inspection_obj.search([('month', '>=', months)]):
                    child_health_schedule_obj.create({
                        'partner_id': self.id, # 儿童
                        'month': child_health_inspection.month, # 月龄
                        'main_point': child_health_inspection.main_point, # 检查重占
                        'item_ids': [(6, 0, [item.id for item in child_health_inspection.item_ids])],
                    })

        return result

