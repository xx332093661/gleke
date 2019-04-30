# -*- encoding:utf-8 -*-
from datetime import datetime, timedelta
import importlib
import logging

from odoo import api
from odoo import fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.exceptions import Warning

_logger = logging.getLogger(__name__)
module = {}


class ScheduleShift(models.Model):
    _name = 'his.schedule_shift'
    _description = '排班班次'
    update_external = True  # 更新外部服务器数据


    department_id = fields.Many2one('hr.department', '科室')
    employee_id = fields.Many2one('hr.employee', '医生')
    schedule_id = fields.Many2one('his.work_schedule', '安排', ondelete='cascade')
    expired = fields.Boolean(compute='get_expired', string='是否过期')
    shift_type_id = fields.Many2one('his.shift_type', '班次')
    register_source_ids = fields.One2many('his.register_source', 'shift_id', '号源')
    start_time = fields.Float('上班时间')
    end_time = fields.Float('下班时间')
    register_time_interval = fields.Char('挂号时间间隔')
    limit = fields.Integer('限号数')
    is_stop = fields.Boolean('是否停诊')
    date = fields.Date('日期', related='schedule_id.date')


    @api.multi
    @api.depends('schedule_id')
    def get_expired(self):
        for obj in self:
            if not obj.schedule_id.date:
                obj.expired = False
            else:
                time_point_name = datetime.strptime(obj.schedule_id.date, DATE_FORMAT) + timedelta(hours=obj.end_time - 8)
                if datetime.now() > time_point_name:
                    obj.expired = True
                else:
                    obj.expired = False


    @api.onchange('is_stop')
    def onchange_is_stop(self):
        reserve_record_obj = self.env['his.reserve_record']  # 预约记录
        refund_apply_obj = self.env['his.refund_apply'].sudo()  # 退款申请
        register_plan_obj = self.env['his.register_plan'] # 队列计划
        register_plan_line_obj = self.env['his.register_plan_line'] # 队列计划明细

        if not module:
            module.update({
                'emqtt': importlib.import_module('odoo.addons.his_app_hcfy.models.emqtt'),
                'config': importlib.import_module('odoo.tools.config')
            })

        _logger.info(u'班次状态:%s', self.is_stop)
        if self.is_stop:
            _logger.info(u'原来状态没有停诊')
            self.env.cr.execute('update his_schedule_shift set is_stop=true where id=%d' % self.env.context['id'])
            # 停诊后，所有的预约记录取消
            message = []
            for register_source in self.register_source_ids:
                if register_source.state != '1':
                    continue

                reserve_record = reserve_record_obj.search([('register_source_id', '=', register_source.id), ('state', '=', 'reserve')])
                if not reserve_record:
                    continue

                _logger.info(register_source.time_point_name)
                # 取消订单
                order = reserve_record.order_id
                order.action_cancel()

                # 更新预约记录
                reserve_record.write({
                    'state': 'cancel',
                    'cancel_type': '2',  # 停诊取消
                })

                refund_apply_internal_id = False
                if order.pay_method != 'free':
                    # 创建退款申请
                    res = {
                        'visit_partner_id': reserve_record.partner_id.id,
                        'pay_method': order.pay_method,
                        'amount_total': order.amount_total,
                        'order_ids': [(6, 0, [order.id])],
                        'state': 'draft',
                        'order_type': order.order_type,
                        'reason': '停诊,取消预约挂号'
                    }
                    if order.pay_method == 'weixin':
                        res.update({
                            'weixin_pay_ids': [(6, 0, [weixin_pay.id for weixin_pay in order.weixin_pay_ids])],
                            'transaction_id': order.weixin_pay_ids[0].transaction_id
                        })
                    if order.pay_method == 'alipay':
                        res.update({
                            'alipay_ids': [(6, 0, [alipay.id for alipay in order.alipay_ids])],
                            'trade_no': order.alipay_ids[0].trade_no
                        })
                    refund_apply = refund_apply_obj.create(res)
                    refund_apply_internal_id = refund_apply.id

                # 更改号源状态
                _logger.info('MMMMMMMMM:%s', register_source.state)
                register_source.write({
                    'state': '0',
                    'lock_time': None
                })
                _logger.info('MMMMMMMMM:%s', register_source.state)
                # 修改队列计划
                register_plan = register_plan_obj.search([('medical_date', '=', reserve_record.reserve_date),
                                                          ('department_id', '=', reserve_record.department_id.id),
                                                          ('employee_id', '=', reserve_record.employee_id.id)])
                if register_plan:
                    register_plan_line = register_plan_line_obj.search([('register_plan_id', '=', register_plan.id), (
                    'time_point_name', '=', reserve_record.register_source_id.time_point_name)])
                    if register_plan_line:
                        register_plan_line.write({
                            'partner_id': False,
                            'source': False,
                            'register_time': False,
                            'reserve_time_point_name': False
                        })

                message.append({
                    'reserve_record_id': reserve_record.id,  # 预约记录内部ID
                    'refund_apply_internal_id': refund_apply_internal_id,  # 退款申请内部ID
                })

            if message:
                payload = {
                    'action': 'schedule_shift_stop',
                    'data': message
                }
                module['emqtt'].Emqtt.publish(module['config'].config['extranet_topic'], payload, 2)

        else:
            _logger.info(u'原来状态是停诊')
            self.env.cr.execute('update his_schedule_shift set is_stop=false where id=%d' % self.env.context['id'])


        # 发送消息
        payload = {
            'action': 'write',
            'data': {
                'model': 'his.schedule_shift',
                'vals': {
                    'internal_id': self.env.context['id'],
                    'is_stop': self.is_stop
                },
            }
        }


        module['emqtt'].Emqtt.publish(module['config'].config['extranet_topic'], payload, 2)


        self.env.cr.commit()





    @api.multi
    def unlink(self):
        for register_source in self.register_source_ids:
            if register_source.state == '1':
                raise Warning('排班已经有人挂号，不能删除，请停诊')

        return super(ScheduleShift, self).unlink()







