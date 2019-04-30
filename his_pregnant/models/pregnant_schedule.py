# -*- coding: utf-8 -*-
from odoo import api
from odoo import models, fields


class PregnantPersonalSchedule(models.Model):
    _name = 'his.pregnant_personal_schedule'
    _description = '孕妇产检计划'
    _order = 'number'
    _rec_name = 'number_label'
    update_external = True  # 更新外部服务器数据

    @api.model
    def _default_number_label(self):
        for obj in self:
            obj.number_label = u'第%s次产检' % obj.number


    partner_id = fields.Many2one('res.partner', '孕妇')
    start_cycle_id = fields.Many2one('his.pregnant_cycle', '开始孕周')
    end_cycle_id = fields.Many2one('his.pregnant_cycle', '截止孕周')
    main_point = fields.Text('产检重点')
    purpose = fields.Text('产检目的')
    preparation = fields.Text('产检准备')
    precautions = fields.Text('注意事项', help='温馨提示')
    item_ids = fields.Many2many('his.pregnant_inspection_item', 'his_pregnant_personal_schedule_item_rel', 'inspection_id', 'item_id', '检查项目')
    number = fields.Integer('次数')
    number_label = fields.Char('检查顺序', compute=_default_number_label)
    state = fields.Selection([('0', '未检查'), ('1', '已检查')], '状态', default='0')


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













