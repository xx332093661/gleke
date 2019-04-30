# coding: utf-8

from odoo import models, fields, api

import logging
import traceback

_logger = logging.getLogger(__name__)


class HrpBusiness(models.Model):
    _name = 'hrp.business'
    _description = u'业务类型'

    name = fields.Char('名称')
    group_num = fields.Integer('组号')
    priority = fields.Integer('优先级')
    business_department_ids = fields.One2many('hrp.business_department', 'business_id', '科室')
    is_free = fields.Boolean('免费')
    is_replace_dept = fields.Boolean('替换同步科室')
    retain_day = fields.Integer('保留天数', default=1)
    record_count = fields.Boolean('记录次数')
    business_category = fields.Selection([('1', '门诊'), ('2', '检验'), ('3', '检查'), ('4', '治疗'), ('5', '手术'), ('6', '发药')], '分类')


class HrpBusinessDepartment(models.Model):
    _name = 'hrp.business_department'
    _description = u'业务科室'

    business_id = fields.Many2one('hrp.business', '业务类型')
    department_id = fields.Many2one('hr.department', '科室')
    is_auto_confirm = fields.Boolean('自动签到')
    auto_confirm_time = fields.Integer('自动签到时间')
    is_write_room = fields.Boolean('分配诊室')
    reconfirm_time = fields.Integer('过号重新签到时间')
    stage_new_num = fields.Boolean('回诊重新编号', default=False)

    return_visit_enable = fields.Boolean('启用复诊')
    doctor_necessary = fields.Boolean('必须挂医生')


class HrpQueueRule(models.Model):
    _name = 'hrp.queue_rule'
    _description = u'调度规则'

    business_id = fields.Many2one('hrp.business', '业务类型')
    department_id = fields.Many2one('hr.department', '科室')
    line_ids = fields.One2many('hrp.queue_rule_line', 'rule_id', '明细')

    _rec_name = 'business_id'

    def get_room_by_rule(self, queue, room_ids):
        """根据调度规则获取诊室"""
        rules = self.search([('business_id.name', '=', queue.business), ('department_id', '=', queue.department_id.id)])
        if not rules:
            return
        data = queue.read()[0]
        for line in rules[0].line_ids:
            if not data[line.queue_field]:
                continue
            f = data[line.queue_field].split(',')
            v = line.value.split(',')
            try:
                res = eval("set(%s).issubset(%s)" %(f, v))
            except Exception:
                _logger.error(traceback.format_exc())
                return
            if res:
                room_ids += line.room_ids.ids


class HrpQueueRuleLine(models.Model):
    _name = 'hrp.queue_rule_line'
    _description = u'规则明细'

    rule_id = fields.Many2one('hrp.queue_rule', '调度规则')
    queue_field = fields.Selection([('register_type', '号类'),
                                    ('part', '部位'),
                                    ('origin', '病人来源'),
                                    ('coll_method', '采集方式'),
                                    ('is_emerg_treat', '加急'),
                                    ('stage', '阶段'),
                                    ('return_visit', '复诊')], '队列字段')
    # relation = fields.Selection([('in', 'in'), ('==', '=')], '关系', default='==')
    value = fields.Char('值')
    room_ids = fields.Many2many('hr.department', 'rule_line_room_rel', 'rule_line_id', 'room_id', '诊室')

    @api.model
    def default_get(self, fields_list):
        """过滤数据(线路)"""
        rule_id = self.env.context.get('rule_id')
        res = super(HrpQueueRuleLine, self).default_get(fields_list)
        if rule_id:
            res.update({'rule_id': rule_id})

        return res
