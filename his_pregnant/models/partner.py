# -*- encoding:utf-8 -*-
from odoo import fields, models, api
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.exceptions import Warning


class Partner(models.Model):
    _inherit = 'res.partner'

    last_menstruation_day = fields.Date('末次月经日期', default=lambda self: datetime.now().strftime(DATE_FORMAT))
    plan_born_day = fields.Date('预产期', default=lambda self: (datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT) + timedelta(days=280)).strftime(DATE_FORMAT))
    current_cycle = fields.Char('当前孕周', compute='_compute_current_cycle')
    born_days = fields.Char('距离预产期', compute='_compute_born_days')
    pregnant_count = fields.Selection([(str(i), '第%d次怀孕' % i) for i in range(1, 20, 1)], '孕次', default='1')
    childbirth_count = fields.Selection([(str(i), '%d胎' % i) for i in range(0, 20, 1)], '产次(产过几胎)', default='0')
    person_liable = fields.Char('产检责任人')
    mother_inspection_ids = fields.One2many('his.mother_inspection', 'partner_id', '产检记录')
    pregnant_personal_schedule_ids = fields.One2many('his.pregnant_personal_schedule', 'partner_id', '产检计划')

    pregnant_in_self = fields.Boolean('在本院产检')

    _sql_constraints = [
        ('value_uniq', 'check (pregnant_count>=childbirth_count)', '产次不能大于孕次')
    ]

    @api.model
    def _compute_current_cycle(self):
        today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)
        for record in self:
            if not record.last_menstruation_day:
                continue

            pregnant_days = (today - datetime.strptime(record.last_menstruation_day, DATE_FORMAT)).days  # 怀孕天数
            born_days = (datetime.strptime(record.plan_born_day, DATE_FORMAT) - today).days
            if born_days < -30:
                current_cycle = 40
                days = 0
            else:
                current_cycle, days = divmod(pregnant_days, 7)
            record.current_cycle = u'孕%d周+%d天' % (current_cycle, days) if days else u'孕%d周' % current_cycle

    @api.onchange('pregnant_count', 'childbirth_count')
    def onchange_pregnant_count(self):
        if self.pregnant_count and self.childbirth_count:
            if int(self.childbirth_count) > int(self.pregnant_count):
                return {
                    'warning': {
                        'title': '孕产次错误',
                        'message': "产次不能大于孕次"
                    }
                }





    @api.model
    def _compute_born_days(self):
        today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)
        for record in self:
            if not record.plan_born_day:
                continue

            born_days = (datetime.strptime(record.plan_born_day, DATE_FORMAT) - today).days
            if born_days < -30:
                born_days = 0
            record.born_days = u'%d天' % born_days


    @api.onchange('last_menstruation_day', 'plan_born_day')
    def onchange_last_menstruation_day(self):
        today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)

        if self._context.get('last_menstruation_day'):
            if self.last_menstruation_day:
                if datetime.strptime(self.last_menstruation_day, DATE_FORMAT) > today:
                    return {
                        'warning': {
                            'title': '末次月经日期错误',
                            'message': "末次月经日期不能大于当前日期"
                        },
                        'value': {
                            'plan_born_day': False,
                            'current_cycle': False,
                            'born_days': False
                        }
                    }

                if datetime.strptime(self.last_menstruation_day, DATE_FORMAT) <= today - timedelta(days=280):
                    return {
                        'warning': {
                            'title': '末次月经日期错误',
                            'message': "末次月经日期值太小了"
                        },
                        'value': {
                            'plan_born_day': False,
                            'current_cycle': False,
                            'born_days': False
                        }
                    }

                self.plan_born_day = (datetime.strptime(self.last_menstruation_day, DATE_FORMAT) + timedelta(days=280)).strftime(DATE_FORMAT)
            else:
                self.plan_born_day = False

        if self._context.get('plan_born_day'):
            if self.plan_born_day:
                if datetime.strptime(self.plan_born_day, DATE_FORMAT) > today + timedelta(days=280):
                    return {
                        'warning': {
                            'title': '预产期错误',
                            'message': "预产期值太大了"
                        },
                        'value': {
                            'last_menstruation_day': False,
                            'current_cycle': False,
                            'born_days': False
                        }
                    }

                if datetime.strptime(self.plan_born_day, DATE_FORMAT) < today:
                    return {
                        'warning': {
                            'title': '预产期错误',
                            'message': "预产期不能小于当前日期"
                        },
                        'value': {
                            'last_menstruation_day': False,
                            'current_cycle': False,
                            'born_days': False
                        }
                    }


                self.last_menstruation_day = (datetime.strptime(self.plan_born_day, DATE_FORMAT) - timedelta(days=280)).strftime(DATE_FORMAT)
            else:
                self.last_menstruation_day = False


        if self.last_menstruation_day:
            pregnant_days = (today - datetime.strptime(self.last_menstruation_day, DATE_FORMAT)).days  # 怀孕天数
            current_cycle, days = divmod(pregnant_days, 7)
            self.current_cycle = u'孕%d周+%d天' % (current_cycle, days) if days else u'孕%d周' % current_cycle
        else:
            self.current_cycle = False

        if self.plan_born_day:
            self.born_days = u'%d天' % (datetime.strptime(self.plan_born_day, DATE_FORMAT) - today).days
        else:
            self.born_days = False


    @api.model
    def create(self, vals):
        pregnant_register_obj = self.env['his.pregnant_register'] # 产检登记
        pregnant_personal_schedule_obj = self.env['his.pregnant_personal_schedule'] # 孕妇产检计划
        pregnant_inspection_obj = self.env['his.pregnant_inspection'] # 产检计划

        today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)

        # 计算预产期、末次月经日期、产检医院
        if vals.get('patient_property') == 'pregnant':
            if not vals['last_menstruation_day'] and not vals['plan_born_day']:
                raise Warning('请填写末次月经日期或预产期!')

            if datetime.strptime(vals['last_menstruation_day'], DATE_FORMAT) > today:
                raise Warning('末次月经日期不能大于当前日期!')

            if datetime.strptime(vals['last_menstruation_day'], DATE_FORMAT) <= today - timedelta(days=280):
                raise Warning('末次月经日期值太小了!')

            if datetime.strptime(vals['plan_born_day'], DATE_FORMAT) > today + timedelta(days=280):
                raise Warning('预产期值太大了!')

            if datetime.strptime(vals['plan_born_day'], DATE_FORMAT) < today:
                raise Warning('预产期不能小于当前日期!')

            if self.env.context.get('patient_property') == 'pregnant': # 通过视图创建
                id_no = vals['id_no']
                if not self.check_identity(vals['id_no']): # 验证身份证
                    raise Warning('身份证号错误!')

                if vals['pregnant_count'] and vals['childbirth_count']:
                    if int(vals['pregnant_count']) < int(vals['childbirth_count']):
                        raise Warning('产次不能大于孕次')

                vals['pregnant_in_self'] = True # 在本院做产检
                vals['birth_date'] = '%s-%s-%s' % (id_no[6:10], id_no[10:12], id_no[12:14])

            else: # 通过接口创建
                pregnant_register = pregnant_register_obj.search([('pregnant_identity_no', '=', vals['id_no'])], order='register_date desc', limit=1) # 产检登记
                if pregnant_register:
                    # id_no = vals['id_no'] # 身份证号
                    vals['pregnant_in_self'] = True  # 在本院做产检
                    vals['pregnant_count'] = pregnant_register.pregnant_count  # 孕次
                    vals['childbirth_count'] = pregnant_register.childbirth_count  # 产次
                    # vals['birth_date'] = '%s-%s-%s' % (id_no[6:10], id_no[10:12], id_no[12:14])


        partner = super(Partner, self).create(vals)
        # 生成产检计划
        if vals.get('patient_property') == 'pregnant':
            if partner.pregnant_in_self: # 在本院做产检

                pregnant_days = (today - datetime.strptime(partner.last_menstruation_day, DATE_FORMAT)).days  # 怀孕天数
                current_cycle = pregnant_days / 7

                pregnant_inspections = pregnant_inspection_obj.search([('end_cycle_id.value', '>=', current_cycle)], order='number')  # 产检计划
                for pregnant_inspection in pregnant_inspections:
                    pregnant_personal_schedule_obj.create({
                        'partner_id': partner.id,
                        'start_cycle_id': pregnant_inspection.start_cycle_id.id,  # 开始孕周
                        'end_cycle_id': pregnant_inspection.end_cycle_id.id,  # 截止孕周
                        'main_point': pregnant_inspection.main_point,  # 产检重点
                        'purpose': pregnant_inspection.purpose,  # 产检目的
                        'preparation': pregnant_inspection.preparation,  # 产检准备
                        'precautions': pregnant_inspection.precautions,  # 注意事项
                        'number': pregnant_inspection.number,  # 检查顺序
                        'item_ids': [(6, 0, [item.id for item in pregnant_inspection.item_ids])],  # 检查项目
                    })

        return partner


    @api.multi
    def write(self, vals):
        pregnant_register_obj = self.env['his.pregnant_register']  # 产检登记
        pregnant_personal_schedule_obj = self.env['his.pregnant_personal_schedule'] # 孕妇产检计划
        pregnant_inspection_obj = self.env['his.pregnant_inspection'] # 产检计划

        today = datetime.strptime(datetime.now().strftime(DATE_FORMAT), DATE_FORMAT)
        if self.patient_property == 'pregnant' or vals.get('patient_property') == 'pregnant':
            if 'last_menstruation_day' in vals:
                if not vals['last_menstruation_day'] and not vals['plan_born_day']:
                    raise Warning('请填写末次月经日期或预产期!')

                if datetime.strptime(vals['last_menstruation_day'], DATE_FORMAT) > today:
                    raise Warning('末次月经日期不能大于当前日期!')

                if datetime.strptime(vals['last_menstruation_day'], DATE_FORMAT) <= today - timedelta(days=280):
                    raise Warning('末次月经日期值太小了!')

                if datetime.strptime(vals['plan_born_day'], DATE_FORMAT) > today + timedelta(days=280):
                    raise Warning('预产期值太大了!')

                if datetime.strptime(vals['plan_born_day'], DATE_FORMAT) < today:
                    raise Warning('预产期不能小于当前日期!')

            if self.env.context.get('patient_property') == 'pregnant':  # 通过视图修改
                if 'id_no' in vals:
                    id_no = vals['id_no']
                    if not self.check_identity(id_no):  # 验证身份证
                        raise Warning('身份证号错误!')

                    vals['birth_date'] = '%s-%s-%s' % (id_no[6:10], id_no[10:12], id_no[12:14])

            if 'patient_property' not in self.env.context: # 通过接口修改
                if 'id_no' in vals and self.id_no != vals['id_no']: # 修改了身份证号
                    pregnant_register = pregnant_register_obj.search([('pregnant_identity_no', '=', vals['id_no'])])  # 产检登记
                    if pregnant_register:
                        vals['pregnant_in_self'] = True  # 在本院做产检
                    else:
                        if self.pregnant_in_self:
                            vals['pregnant_in_self'] = False  # 不在本院做产检

        result = super(Partner, self).write(vals)
        if self.patient_property != 'pregnant':
            return result

        if 'last_menstruation_day'in vals or 'pregnant_in_self' in vals:
            pregnant_personal_schedule_obj.search([('partner_id', '=', self.id)]).unlink()  # 删除原有计划

            if self.pregnant_in_self: # 在本院做产检

                pregnant_days = (today - datetime.strptime(self.last_menstruation_day, DATE_FORMAT)).days  # 怀孕天数
                current_cycle = pregnant_days / 7

                pregnant_inspections = pregnant_inspection_obj.search([('end_cycle_id.value', '>=', current_cycle)], order='number')  # 产检计划

                for pregnant_inspection in pregnant_inspections:
                    pregnant_personal_schedule_obj.create({
                        'partner_id': self.id,
                        'start_cycle_id': pregnant_inspection.start_cycle_id.id,  # 开始孕周
                        'end_cycle_id': pregnant_inspection.end_cycle_id.id,  # 截止孕周
                        'main_point': pregnant_inspection.main_point,  # 产检重点
                        'purpose': pregnant_inspection.purpose,  # 产检目的
                        'preparation': pregnant_inspection.preparation,  # 产检准备
                        'precautions': pregnant_inspection.precautions,  # 注意事项
                        'number': pregnant_inspection.number,  # 检查顺序
                        'item_ids': [(6, 0, [item.id for item in pregnant_inspection.item_ids])],  # 检查项目
                    })


        return super(Partner, self).write(vals)
