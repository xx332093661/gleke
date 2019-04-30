# -*- encoding:utf-8 -*-
import logging
import threading
import traceback

from odoo import api
from odoo import models, fields

_logger = logging.getLogger(__name__)


class OutpatientFee(models.Model):
    _name = 'his.outpatient_fee'
    _description = '门诊费用记录'
    _order = 'id desc'
    create_lock = threading.Lock()

    his_id = fields.Integer('HISID', index=True, help='医嘱ID')

    record_prototype = fields.Integer('记录性质')
    receipt_no = fields.Char('挂号单')
    record_state = fields.Integer('记录状态')
    serial_number = fields.Integer('序号')

    partner_id = fields.Many2one('res.partner', '病人')

    dispose_serial_number = fields.Integer('医嘱序号')
    dispose_id = fields.Many2one('his.dispose', '医嘱')
    win_num = fields.Char('发药窗口')
    exe_state = fields.Integer('执行状态')
    exe_datetime = fields.Char('执行时间')

    register_datetime = fields.Char('登记时间')
    register_date = fields.Date('登记日期', help='通过"登记时间"计算出来')

    is_history = fields.Boolean('历史记录')

    _sql_constraints = [('his_id_uniq', 'unique (his_id)', u'his_id必须唯一!')]


    @api.model
    def create(self, res):
        with OutpatientFee.create_lock:
            outpatient_fee = self.search([('his_id', '=', res['his_id'])])
            if not outpatient_fee:
                try:
                    partner_id = False
                    if res['partner_his_id']:
                        partner_id = self.env['res.partner'].search([('his_id', '=', res['partner_his_id'])]).id

                    dispose_id = False
                    if res['dispose_id']:
                        dispose = self.env['his.dispose'].search([('his_id', '=', res['dispose_id'])])
                        if dispose:
                            dispose_id = dispose.id

                    vals = {
                        'his_id': res['his_id'],  # HISID
                        'record_prototype': res['record_prototype'],  # 记录性质
                        'receipt_no': res['receipt_no'],  # NO(单据号)
                        'record_state': res['record_state'],  # 记录状态
                        'serial_number': res['serial_number'],  # 序号
                        'partner_id': partner_id,  # 病人
                        'dispose_serial_number': res['dispose_id'],  # 医嘱序号
                        'dispose_id': dispose_id,  # 医嘱
                        'win_num': res['win_num'],  # 发药窗口
                        'exe_state': res['exe_state'],  # 执行状态
                        'exe_datetime': res['exe_datetime'],  # 执行时间
                        'register_datetime': res['register_datetime'],  # 发生时间
                        'register_date': res['register_datetime'].split()[0],  # 发生日期
                    }

                    outpatient_fee = super(OutpatientFee, self).create(vals)
                    self.env.cr.commit()
                except:
                    self.env.cr.rollback()
                    _logger.warn(u'创建门诊费用记录出错')
                    _logger.error(traceback.format_exc())
                    outpatient_fee = self.search([('his_id', '=', res['his_id'])])

            else:
                vals = {}
                if outpatient_fee.record_state != res['record_state']:
                    vals['record_state'] = res['record_state']

                win_num = res['win_num']
                if win_num:
                    win_num = win_num.decode('utf8')

                    if outpatient_fee.win_num != win_num:
                        vals['win_num'] = res['win_num']

                if outpatient_fee.exe_state != res['exe_state']:
                    vals['exe_state'] = res['exe_state']

                if outpatient_fee.exe_datetime != res['exe_datetime']:
                    vals['exe_datetime'] = res['exe_datetime']

                if not outpatient_fee.dispose_id:
                    if res['dispose_id']:
                        dispose = self.env['his.dispose'].search([('his_id', '=', res['dispose_id'])])
                        if dispose:
                            vals['dispose_id'] = dispose.id
                if vals:
                    outpatient_fee.write(vals)
                    self.env.cr.commit()


        return outpatient_fee


