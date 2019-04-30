# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from makePinyin import pinyinAbbr
from odoo.exceptions import UserError


class HrDepartment(models.Model):

    _inherit = 'hr.department'

    @api.multi
    def _get_pinyin(self):
        for obj in self:
            name = obj.name
            pinyins = pinyinAbbr(name)
            if pinyins:
                obj.pinyin = pinyins[0]

    id = fields.Integer('科室ID')
    code = fields.Char('科室编码')
    show_name = fields.Char('显示名称')
    pinyin = fields.Char('拼音', compute=_get_pinyin)
    display_seq = fields.Integer('显示顺序')

    location = fields.Char('位置')

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        department_id = self.env.context.get('department_id')
        if department_id:
            # 根据科室过滤诊室
            args += [('parent_id', '=', department_id)]

        return super(HrDepartment, self).name_search(name, args, operator=operator, limit=limit)

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.parent_id:
                name = "%s / %s" % (record.parent_id.name, name)
            result.append((record.id, name))
        return result


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.multi
    def _get_pinyin(self):
        for obj in self:
            name = obj.name
            pinyins = pinyinAbbr(name)
            if pinyins:
                obj.pinyin = pinyins[0]

    # code = fields.Char('人员编号')
    introduction = fields.Text('简介')
    registered_type_ids = fields.Many2many('hrp.registered.type', 'employee_registered_type_rel', 'employee_id',
                                           'registered_type_id', '所看号类')
    role = fields.Selection([('doctor', '医生'), ('nurse', '护士'), ('manager', '管理员')], '角色')

    queue_ids = fields.One2many('hrp.queue', 'operation_employee_id', '接诊队列')
    department_ids = fields.Many2many('hr.department', 'employee_department_rel', 'employee_id', 'department_id', '科室')

    def create_user(self, name, code):
        """创建用户"""
        m_users = self.env['res.users']
        # 消重
        users = m_users.search([('login', '=', code)])
        if users:
            raise UserError(_(u'用户名已被占用'))
        user = m_users.create({
            'name': name,
            'login': code,
            'password': code,
        })
        return user.id

    # @api.model
    # def create(self, vals):
    #     """如果创建的员工有用户和角色，赋予对应权限"""
    #     if vals.get('user_id') and vals.get('role'):
    #         # 赋予权限
    #         self.set_right(vals['user_id'], vals['role'])
    #
    #     return super(HrEmployee, self).create(vals)
    #
    # @api.multi
    # def write(self, val):
    #     for s in self:
    #         if val.get('role') and (val.get('user_id') or s.user_id):
    #             user_id = val.get('user_id') or s.user_id.id
    #             # 赋予权限
    #             self.set_right(user_id, val['role'])
    #     return super(HrEmployee, self).write(val)

    def set_right(self, user_id, role):
        """设置用户权限"""
        m_groups = self.env(user=1)['res.groups']
        # 清除该用户所有权限
        groups = m_groups.search([])
        for g in groups:
            g.write({'users': [(3, user_id)]})
        # 设置权限
        res_groups = []
        group1 = None
        if role == 'doctor':
            # 医生
            group1 = self.env['ir.model.data'].xmlid_to_object('hrp_queue.group_hrp_doctor')
            # 人力资源用户权限
            group2 = self.env['ir.model.data'].xmlid_to_object('base.group_user')
            if group2:
                res_groups.append(group2)
        elif role == 'nurse':
            # 护士
            group1 = self.env['ir.model.data'].xmlid_to_object('hrp_queue.group_hrp_nurse')
            # 人力资源用户权限
            group2 = self.env['ir.model.data'].xmlid_to_object('base.group_user')
            if group2:
                res_groups.append(group2)
        elif role == 'manager':
            group1 = self.env['ir.model.data'].xmlid_to_object('hrp_queue.group_hrp_manager')
            # 人力资源管理权限
            group4 = self.env['ir.model.data'].xmlid_to_object('hr.group_hr_user')
            if group4:
                res_groups.append(group4)
            # 创建联系人
            group6 = self.env['ir.model.data'].xmlid_to_object('base.group_partner_manager')
            if group6:
                res_groups.append(group6)

        if group1:
            res_groups.append(group1)
        for g in res_groups:
            g.write({'users': [(4, user_id)]})
        return 1

    # @XmlrpcInterfaceWraps(
    #     funcid='1201001',
    #     model='hr.employee',
    #     description=u'获取当前登录用户的信息',
    #     data_format="",
    #     return_format="",
    # )
    def get_employee_data(self, user, employee, arg, context=None):
        if not employee:
            return [], 0, u'员工为空'

        result = {
            'id': employee.id,
            'code': employee.code,
            'photo_url': '/web/image/%s/%s/image' % (employee._name, employee.id),
            'name': employee.name,
            'registered_types': [tp.name for tp in employee.registered_type_ids],
            'introduction': employee.introduction,
        }
        return result


class HrpRegisteredType(models.Model):
    _name = 'hrp.registered.type'
    _description = u'号类'

    name = fields.Char('名称')

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if self.env.context.get('employee_id'):
            args += [('id', 'in', self.env['hr.employee'].browse(self.env.context['employee_id']).registered_type_ids.ids)]
        return super(HrpRegisteredType, self).name_search(name, args=args, operator=operator, limit=limit)