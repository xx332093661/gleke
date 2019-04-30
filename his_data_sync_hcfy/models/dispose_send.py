# -*- encoding:utf-8 -*-
import logging
import threading
import traceback

from odoo import api
from odoo import models, fields

_logger = logging.getLogger(__name__)


class DisposeSend(models.Model):
    _name = 'his.dispose_send'
    _description = '病人医嘱发送'
    _order = 'id desc'
    create_lock = threading.Lock()

    # TODO 创建索引 名称:his_dispose_send_send_no_dispose_serial_number 字段:send_no, dispose_serial_number

    send_no = fields.Integer('发送号')
    dispose_serial_number = fields.Integer('医嘱ID')
    send_datetime = fields.Char('发送时间')
    send_date = fields.Char('发送日期')
    exe_room = fields.Char('执行间')
    exe_process = fields.Char('执行过程')
    register_datetime = fields.Char('报到时间')

    dispose_id = fields.Many2one('his.dispose', '医嘱')

    is_history = fields.Boolean('历史记录')

    # _sql_constraints = [('send_no_dispose_serial_number_uniq', 'unique (send_no, dispose_serial_number)', u'发送号、医嘱序号必须唯一!')]

    @api.model
    def create(self, vals):
        with DisposeSend.create_lock:
            dispose_send = self.search([('send_no', '=', vals['send_no']), ('dispose_serial_number', '=', vals['dispose_id'])])
            if not dispose_send:
                try:
                    dispose_send = super(DisposeSend, self).create(vals)
                    self.env.cr.commit()
                except:
                    self.env.cr.rollback()
                    _logger.warn(u'创建病人医嘱发送出错')
                    _logger.error(traceback.format_exc())
                    dispose_send = self.search([('send_no', '=', vals['send_no']), ('dispose_serial_number', '=', vals['dispose_id'])])

            else:
                res = {}
                if dispose_send.exe_room != vals['exe_room']:
                    res['exe_room'] = vals['exe_room']

                if dispose_send.exe_process != vals['exe_process']:
                    res['exe_process'] = res['exe_process']

                if dispose_send.register_datetime != vals['register_datetime']:
                    res['register_datetime'] = vals['register_datetime']

                if res:
                    dispose_send.write(res)
                    self.env.cr.commit()

        return dispose_send




