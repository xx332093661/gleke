# -*- encoding:utf-8 -*-
from odoo import fields, models, api


class Company(models.Model):
    _inherit = 'res.company'

    internal_id = fields.Integer('内部id')
    topic = fields.Char('主题')
    longitude = fields.Char('经度')
    latitude = fields.Char('纬度')
    range = fields.Integer('定位精度(米)')
    appoint_day = fields.Integer('挂号预约天数')
    state = fields.Selection([('0', '停用'), ('1', '启用')], '状态', default='1')

    app_function_ids = fields.Many2many('hrp.app_function', 'company_func_rel', 'company_id', 'app_function_id', 'app功能')

    # 微信
    weixin_appid = fields.Char('微信应用ID')
    weixin_mch_id = fields.Char('商户号')
    weixin_api_key = fields.Char('秘钥')

    # 支付宝
    alipay_app_id = fields.Char('支付宝应用ID')
    app_alipay_private_key = fields.Binary('应用私钥', attachment=True)
    app_alipay_private_key_path = fields.Char('应用私钥', compute='_compute_key_patch')

    app_alipay_public_key = fields.Binary('应用公钥', attachment=True)
    app_alipay_public_key_path = fields.Char('应用公钥', compute='_compute_key_patch')

    # 建行龙支付
    long_mch_id = fields.Char('龙支付商户号')
    long_counter_id = fields.Char('龙支付柜台号')
    long_branch_code = fields.Char('龙支付分行代码')
    long_mch_phone = fields.Char('龙支付商户手机号')
    long_key = fields.Text('龙支付秘钥')



    @api.multi
    def _compute_key_patch(self):
        attachment_obj = self.env['ir.attachment']

        for company in self:
            if company.app_alipay_private_key:
                # 私钥路径
                app_alipay_private_key = attachment_obj.search([('res_model', '=', 'res.company'), ('res_id', '=', company.id), ('res_field', '=', 'app_alipay_private_key')], limit=1)
                if app_alipay_private_key:
                    company.app_alipay_private_key_path = attachment_obj._full_path(app_alipay_private_key.store_fname)

            if company.app_alipay_public_key:
                # 公钥路径
                app_alipay_public_key = attachment_obj.search([('res_model', '=', 'res.company'), ('res_id', '=', company.id), ('res_field', '=', 'app_alipay_public_key')], limit=1)
                if app_alipay_public_key:
                    company.app_alipay_public_key_path = attachment_obj._full_path(app_alipay_public_key.store_fname)
