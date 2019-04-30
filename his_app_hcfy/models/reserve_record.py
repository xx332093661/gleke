# -*- encoding:utf-8 -*-
from datetime import datetime, timedelta
import importlib
import logging
import traceback
from odoo import api
from odoo import fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


_logger = logging.getLogger(__name__)

module = {}


class ReserveRecord(models.Model):
    _description = '预约记录'
    _name = 'his.reserve_record'
    _order = 'id desc'


    partner_id = fields.Many2one('res.partner', '患者')
    reserve_date = fields.Date('就诊日期')
    department_id = fields.Many2one('hr.department', '科室')
    employee_id = fields.Many2one('hr.employee', '医生')

    shift_type_id = fields.Many2one('his.shift_type', '班次')
    register_source_id = fields.Many2one('his.register_source', '号源')
    # time_point_name = fields.Char('时间点')
    reserve_sort = fields.Char('预约顺序号')
    tran_flow = fields.Char('医院结算流水号')
    receipt_no = fields.Char('挂号单号')


    order_id = fields.Many2one('sale.order', '订单')
    register_id = fields.Many2one('his.register', 'HIS挂号记录')
    type = fields.Selection([('register', '挂号'), ('inoculation', '预防接种'), ('pregnant', '产检'), ('', '体检')], '类别')
    state = fields.Selection([('draft', '草稿'), ('reserve', '预约'), ('commit', '提交HIS'), ('done', '完成'), ('cancel', '取消')], '状态')

    commit_his_state = fields.Selection([('-1', '未提交'), ('0', '提交HIS失败'), ('1', '提交HIS成功')], '提交HIS状态', default='-1')
    cancel_type = fields.Selection([('1', '用户取消'), ('2', '停诊取消')], '取消类别')



    @api.model
    def commit_his(self):
        """预约记录提交到HIS"""

        his_interface_obj = self.env['his.interface'] # HIS接口
        register_plan_obj = self.env['his.register_plan'] # 队列计划
        register_plan_line_obj = self.env['his.register_plan_line'] # 队列计划明细

        today = (datetime.now() + timedelta(hours=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        _logger.info(u'执行预约记录提交到HIS')
        _logger.info(u'当前时间:%s today值:%s', datetime.now(), datetime.now() + timedelta(hours=1))

        payload = []

        for reserve_record in self.search([('state', '=', 'reserve'), ('commit_his_state', '=', '-1'), ('type', 'in', ['register']), ('reserve_date', '=', today)]):
            res = {
                'commit_his_state': '1',  # 提交HIS状态
                'reserve_id': reserve_record.id
            }
            try:
                partner = reserve_record.partner_id # 患者
                result = his_interface_obj.reserve_record_commit_his(reserve_record)

                # 修改预约记录状态
                reserve_record.write({
                    'tran_flow': result['tran_flow'],
                    'receipt_no': result['receipt_no'],
                    'state': 'commit',
                    'commit_his_state': '1'
                })

                # 修改订单状态
                reserve_record.order_id.write({
                    'tran_flow': result['tran_flow'],
                    'receipt_no': result['receipt_no'],
                    'commit_his_state': '1',
                })

                # 修改患者门诊号
                if partner.outpatient_num != result['outpatient_num']:
                    partner.outpatient_num = result['outpatient_num']

            except Exception, e:
                _logger.error(u'预约记录提交HIS发生错误')
                _logger.error(traceback.format_exc())
                res.update({
                    'commit_his_state': '0',
                    'commit_his_error_msg': e.message
                })
                # 修改订单状态
                reserve_record.order_id.write({
                    'commit_his_state': '0',
                    'commit_his_error_msg': e.message
                })
                # 修改预约记录状态
                reserve_record.write({
                    'commit_his_state': '0'
                })
                # 修改号源状态
                reserve_record.register_source_id.state = '0'
                # 修改队列计划状态
                register_plan = register_plan_obj.search([
                    ('medical_date', '=', reserve_record.reserve_date),
                    ('department_id', '=', reserve_record.department_id.id),
                    ('employee_id', '=', reserve_record.employee_id.id)])
                register_plan_line_obj.search([('register_plan_id', '=', register_plan.id), ('time_point_name', '=', reserve_record.register_source_id.time_point_name)]).write({
                    'partner_id': False,
                    'source': False,
                    'register_time': False
                })


            payload.append(res)

        # 向外网发送MQTT消息
        if payload:
            if not module:
                module.update({
                    'emqtt': importlib.import_module('odoo.addons.his_app_hcfy.models.emqtt'),
                    'config': importlib.import_module('odoo.tools.config')
                })

            payload = {
                'action': 'commit_reserve_record',
                'data': payload
            }

            module['emqtt'].Emqtt.publish(module['config'].config['extranet_topic'], payload, 2)




























