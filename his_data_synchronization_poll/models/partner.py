# -*- encoding:utf-8 -*-
import logging
import threading
import traceback
import json

from odoo import api
from odoo import models, fields

_logger = logging.getLogger(__name__)



class Partner(models.Model):
    _inherit = 'res.partner'
    create_lock = threading.Lock()

    # his_id = fields.Integer('HISID', index=True)
    sex = fields.Char('性别')

    # outpatient_num = fields.Char('门诊号')
    hospitalize_no = fields.Char('住院号')
    id_no = fields.Char('身份证号')
    card_no = fields.Char('就诊卡号')
    medical_no = fields.Char('医保号')

    # _sql_constraints = [('his_id_uniq', 'unique (his_id)', u'his_id必须唯一!')]
    #
    #
    # @api.model
    # def create_partner(self, vals):
    #
    #     with Partner.create_lock:
    #         # _logger.info(u'创建合作伙伴入锁')
    #         partner = self.search([('his_id', '=', vals['his_id'])])
    #         if not partner:
    #             try:
    #                 # _logger.info(u'创建合作伙伴, value:%s', json.dumps(vals, ensure_ascii=False, encoding='utf8'))
    #                 vals['customer'] = True
    #                 partner = super(Partner, self).create(vals)
    #                 self.env.cr.commit()
    #             except:
    #                 self.env.cr.rollback()
    #                 _logger.info(u'创建合作伙伴出错')
    #                 _logger.error(traceback.format_exc())
    #                 partner = self.search([('his_id', '=', vals['his_id'])])
    #
    #         else:
    #             val = {}
    #             if vals.get('outpatient_num') and partner.outpatient_num != str(vals['outpatient_num']):
    #                 val['outpatient_num'] = str(vals['outpatient_num'])
    #
    #
    #             if vals.get('hospitalize_no') and partner.hospitalize_no != str(vals['hospitalize_no']):
    #                 val['hospitalize_no'] = str(vals['hospitalize_no'])
    #
    #             if val:
    #                 partner.write(val)
    #
    #
    #         # _logger.info(u'创建合作伙伴出锁')
    #
    #
    #     return partner




