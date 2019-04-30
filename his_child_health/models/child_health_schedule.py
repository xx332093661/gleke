# -*- coding: utf-8 -*-
from odoo import api
from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.exceptions import Warning
from datetime import datetime
from dateutil.relativedelta import relativedelta


class ChildHealthSchedule(models.Model):
    _name = 'his.child_health_schedule'
    _description = '儿保计划'
    _rec_name = 'month_label'
    _order = 'month'


    partner_id = fields.Many2one('res.partner', '儿童', ondelete='cascade')
    month = fields.Integer('月龄')
    month_label = fields.Char('月龄', compute='_compute_month_label')
    main_point = fields.Text('检查重点')
    item_ids = fields.Many2many('his.child_health_inspection_item', 'child_health_schedule_item_rel', 'schedule_id', 'item_id', '检查项目')
    state = fields.Selection([('0', '未检查'), ('1', '已检查')], '状态', default='0')

    @api.multi
    def _compute_month_label(self):
        for item in self:
            item.month_label = u'第%d月' % item.month


    @api.onchange('partner_id')
    def onchange_product_ids(self):
        child_health_cycle_obj = self.env['his.child_health_cycle']  # 儿保周期
        if not self.partner_id:
            cycle = child_health_cycle_obj.search([], order='month asc', limit=1)
            if cycle:
                self.month = cycle.month
            else:
                self.month = 1
        else:
            partner = self.partner_id
            schedule = self.search([('partner_id', '=', partner.id)], order='month desc', limit=1)
            if schedule:
                cycle = child_health_cycle_obj.search([('month', '>', schedule.month)], order='month asc', limit=1)
                if cycle:
                    self.month = cycle.month
                else:
                    self.month = schedule.month + 1
            else:
                cycle = child_health_cycle_obj.search([], order='month asc', limit=1)
                if cycle:
                    self.month = cycle.month
                else:
                    self.month = 1



class ChildInspectionRecord(models.Model):
    _name = 'his.child_inspection_record'
    _description = '儿保记录'
    _rec_name = 'partner_id'
    _order = 'schedule_id'



    partner_id = fields.Many2one('res.partner', '儿童', ondelete='cascade')
    age = fields.Char('年龄', compute='_compute_age', help='儿童当前是几月龄')

    schedule_id = fields.Many2one('his.child_health_schedule', '儿保计划')
    inspection_date = fields.Date('检查日期', default=lambda x: datetime.now().strftime(DATE_FORMAT))
    inspection_doctor = fields.Char('接诊医生')
    detail_ids = fields.One2many('his.child_inspection_record_detail', 'child_inspection_record_id', '儿保明细记录')

    @api.multi
    def _compute_age(self):
        for record in self:
            if not record.partner_id.birth_date or not record.inspection_date:
                continue

            ages = self.compute_newborn_age(record.partner_id.birth_date, record.inspection_date)  # 计算新生儿年龄
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

    @api.model
    def create(self, vals):
        birth_date = datetime.strptime(self.env['res.partner'].browse(vals['partner_id']).birth_date, DATE_FORMAT)
        today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)
        inspection_date = datetime.strptime(vals['inspection_date'], DATE_FORMAT)
        if inspection_date < birth_date:
            raise Warning('检查日期不能小于出生日期!')

        if inspection_date > today:
            raise Warning('检查日期不能大于当天日期')

        record = super(ChildInspectionRecord, self).create(vals)
        record.schedule_id.state = '1'
        return record

    @api.multi
    def write(self, vals):
        if 'inspection_date' in vals:
            birth_date = datetime.strptime(self.env['res.partner'].browse(vals['partner_id']).birth_date, DATE_FORMAT)
            today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)
            inspection_date = datetime.strptime(vals['inspection_date'], DATE_FORMAT)
            if inspection_date < birth_date:
                raise Warning('检查日期不能小于出生日期!')

            if inspection_date > today:
                raise Warning('检查日期不能大于当天日期')

        return super(ChildInspectionRecord, self).write(vals)

    @api.multi
    def unlink(self):
        for record in self:
            if record.schedule_id:
                record.schedule_id.state = '0'
        return super(ChildInspectionRecord, self).unlink()


    @staticmethod
    def compute_newborn_age(birthday, inspection_date):
        """计算新生儿年龄"""
        inspection_date = datetime.strptime(inspection_date, DATE_FORMAT)  # 当前日期
        birthday = datetime.strptime(birthday, DATE_FORMAT)  # 出生日期
        ages = relativedelta(inspection_date, birthday)  # 新生儿年龄
        return ages


    @api.onchange('partner_id', 'inspection_date')
    def onchange_partner_id(self):

        if self.partner_id and self.inspection_date:
            birth_date = datetime.strptime(self.partner_id.birth_date, DATE_FORMAT)
            today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)
            inspection_date = datetime.strptime(self.inspection_date, DATE_FORMAT)
            if inspection_date < birth_date:
                raise Warning('检查日期不能小于出生日期!')

            if inspection_date > today:
                raise Warning('检查日期不能大于当天日期')

        if not self.partner_id or not self.inspection_date:
            age = False
            months = 0
        else:
            ages = self.compute_newborn_age(self.partner_id.birth_date, self.inspection_date)  # 计算新生儿年龄
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

        return {
            'value': {'age': age},
            'domain': {'schedule_id': [('partner_id', '=', self.partner_id.id), ('state', '=', '0'), ('month', '=', months)]}
        }



class ChildInspectionRecordDetail(models.Model):
    _name = 'his.child_inspection_record_detail'
    _description = '儿保记录明细'
    # update_external = True  # 更新外部服务器数据

    child_inspection_record_id = fields.Many2one('his.child_inspection_record', '儿保记录', ondelete='cascade')
    item_id = fields.Many2one('his.child_health_inspection_item', '儿保项目', ondelete='set null')
    department = fields.Char('执行科室')
    result_description = fields.Text('检查结果描述')
    result_image = fields.Binary('结果图像')
    result_assay = fields.Binary('结果化验单')

