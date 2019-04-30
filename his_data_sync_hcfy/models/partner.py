# -*- encoding:utf-8 -*-
import logging
import threading
import traceback

from odoo import api
from odoo import models, fields

_logger = logging.getLogger(__name__)



class Partner(models.Model):
    _inherit = 'res.partner'
    create_lock = threading.Lock()

    his_id = fields.Integer('HISID', index=True)
    # sex = fields.Char('性别')
    #
    # # outpatient_num = fields.Char('门诊号')
    # hospitalize_no = fields.Char('住院号')
    # id_no = fields.Char('身份证号')
    # card_no = fields.Char('就诊卡号')
    # medical_no = fields.Char('医保号')
    #
    _sql_constraints = [('his_id_uniq', 'unique (his_id)', u'his_id必须唯一!')]


    @api.model
    def create_partner(self, vals):
        with Partner.create_lock:
            partner = self.search([('his_id', '=', vals['his_id'])])
            if not partner:
                try:
                    vals['customer'] = True
                    partner = super(Partner, self).create(vals)
                    self.env.cr.commit()
                except:
                    self.env.cr.rollback()
                    _logger.info(u'创建合作伙伴出错')
                    _logger.error(traceback.format_exc())
                    partner = self.search([('his_id', '=', vals['his_id'])])
            else:
                val = {}
                if vals.get('name') and partner.name != vals['name'].decode('utf8'): # 在医嘱发送时改名
                    val['name'] = vals['name']

                if vals.get('outpatient_num') and partner.outpatient_num != str(vals['outpatient_num']):
                    val['outpatient_num'] = str(vals['outpatient_num'])


                if vals.get('hospitalize_no') and partner.hospitalize_no != str(vals['hospitalize_no']):
                    val['hospitalize_no'] = str(vals['hospitalize_no'])

                if vals.get('card_no') and partner.card_no != str(vals['card_no']):
                    val['card_no'] = str(vals['card_no'])

                if vals.get('birth_date') and partner.hospitalize_no != str(vals['birth_date']):
                    val['birth_date'] = str(vals['birth_date'])

                if val:
                    partner.write(val)
                    self.env.cr.commit()

        return partner




