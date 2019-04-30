# -*- coding: utf-8 -*-
from odoo import models, fields
from ..models.emqtt import Emqtt

import uuid


class HrpAppFunction(models.Model):

    _name = 'hrp.app_function'
    _description = u'app功能'

    name = fields.Char('功能名称')
    code = fields.Char('功能编码')
    parent_id = fields.Many2one('hrp.app_function', '父功能')