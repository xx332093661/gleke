# -*- encoding:utf-8 -*-
from datetime import datetime

from odoo import api
from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.exceptions import Warning



class MotherInspection(models.Model):
    _name = 'his.mother_inspection'
    _description = '孕妇产检记录'
    _rec_name = 'partner_id'
    update_external = True  # 更新外部服务器数据

    partner_id = fields.Many2one('res.partner', '孕妇')
    schedule_id = fields.Many2one('his.pregnant_personal_schedule', '孕妇产检计划')
    cycle = fields.Char('孕周', compute='_compute_cycle')
    inspection_date = fields.Date('检查日期', default=lambda self: datetime.now().strftime(DATE_FORMAT))
    inspection_doctor = fields.Char('接诊医生')
    detail_ids = fields.One2many('his.mother_inspection_detail', 'inspection_id', '孕检明细')

    @api.model
    def _compute_cycle(self):
        for record in self:
            last_menstruation_day = record.partner_id.last_menstruation_day # 末次月经日期
            if not last_menstruation_day:
                continue

            inspection_date = datetime.strptime(record.inspection_date, DATE_FORMAT) # 检查日期
            pregnant_days = (inspection_date - datetime.strptime(last_menstruation_day, DATE_FORMAT)).days  # 怀孕天数
            current_cycle, days = divmod(pregnant_days, 7)
            record.cycle = u'孕%d周+%d天' % (current_cycle, days) if days else u'孕%d周' % current_cycle


    @api.onchange('partner_id', 'inspection_date')
    def onchange_partner_id(self):
        if not self.partner_id or not self.inspection_date:
            cycle = False
            schedule_id = False
        else:
            today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)
            last_menstruation_day = datetime.strptime(self.partner_id.last_menstruation_day, DATE_FORMAT) # 末次月经日期
            inspection_date = datetime.strptime(self.inspection_date, DATE_FORMAT) # 检查日期
            if inspection_date < last_menstruation_day:
                raise Warning('检查日期不能小于出生日期!')

            if inspection_date > today:
                raise Warning('检查日期不能大于当天日期')

            pregnant_days = (inspection_date - last_menstruation_day).days  # 怀孕天数
            current_cycle, days = divmod(pregnant_days, 7)
            cycle = u'孕%d周+%d天' % (current_cycle, days) if days else u'孕%d周' % current_cycle

            # 计算对应的产检计划
            schedule_id = False
            schedule_obj = self.env['his.pregnant_personal_schedule'] # 孕妇产检计划
            schedule = schedule_obj.search([('partner_id', '=', self.partner_id.id), ('state', '=', '0'), ('start_cycle_id.value', '<=', current_cycle), ('end_cycle_id.value', '>=', current_cycle)])
            if schedule:
                schedule_id = schedule.id

        return {
            'value': {
                'cycle': cycle,
                'schedule_id': schedule_id
            },
            'domain': {'schedule_id': [('id', '=', schedule_id)]}
        }


    @api.model
    def create(self, vals):
        record = super(MotherInspection, self).create(vals)
        record.schedule_id.state = '1'
        return record

    @api.multi
    def unlink(self):
        for record in self:
            if record.schedule_id:
                record.schedule_id.state = '0'
        return super(MotherInspection, self).unlink()



class MotherInspectionDetail(models.Model):
    _name = 'his.mother_inspection_detail'
    _description = '孕妇产检明细记录'
    update_external = True  # 更新外部服务器数据

    inspection_id = fields.Many2one('his.mother_inspection', '孕妇产检记录')
    item_id = fields.Many2one('his.pregnant_inspection_item', '孕检项目')
    department = fields.Char('执行科室')
    result_description = fields.Text('检查结果描述')
    result_image = fields.Binary('结果图像')
    result_assay = fields.Binary('结果化验单')

