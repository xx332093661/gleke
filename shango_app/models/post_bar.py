# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrpPostChannelCategory(models.Model):
    _name = 'hrp.post_channel_category'
    _description = u'频道分类'

    name = fields.Char('名称')
    attribute = fields.Selection([('1', '讨论'), ('2', '新闻')], '属性', default='1')


class HrpPostChannel(models.Model):
    _name = 'hrp.post_channel'
    _description = u'频道'

    name = fields.Char('名称')
    category_id = fields.Many2one('hrp.post_channel_category', '分类')
    image = fields.Binary('图片')
    introduction = fields.Char('简介')
    partner_ids = fields.Many2many('res.partner', 'partner_post_channel_rel', 'channel_id', 'partner_id', '关注者')
    post_ids = fields.One2many('hrp.post', 'channel_id', '帖子')


class HrpPost(models.Model):
    _name = 'hrp.post'
    _description = u'话题'
    _order = 'create_date desc'

    channel_id = fields.Many2one('hrp.post_channel', '频道')
    title = fields.Char('标题')
    partner_id = fields.Many2one('res.partner', '楼主')
    tag_ids = fields.Many2many('hrp.post_tag', 'post_post_tag_rel', 'post_id', 'tag_id', '标签')

    content_ids = fields.One2many('hrp.post_content', 'post_id', '内容')
    partner_ids = fields.Many2many('res.partner', 'partner_post_rel', 'post_id', 'partner_id', '收藏者')

    @api.model
    def default_get(self, default_fields):
        res = super(HrpPost, self).default_get(default_fields)

        if self._context.get('post_channel_id'):
            post_channel_id = self.env['hrp.post_channel'].search([('id', '=', self._context['post_channel_id'])]).id
            res.update({
                'channel_id': post_channel_id
            })
        return res


class HrpPostContent(models.Model):
    _name = 'hrp.post_content'
    _description = u'内容'
    _rec_name = 'partner_id'

    post_id = fields.Many2one('hrp.post', '帖子')
    partner_id = fields.Many2one('res.partner', '用户')
    content = fields.Text('内容')
    image_ids = fields.One2many('hrp.post_content_image', 'post_content_id', '图片')
    is_main = fields.Boolean('主内容')

    parent_id = fields.Many2one('hrp.post_content', '回复')


class HrpPostContentImage(models.Model):
    _name = 'hrp.post_content_image'
    _description = u'内容图片'

    post_content_id = fields.Many2one('hrp.post_content', '内容')
    image = fields.Binary('图片')


class HrpPostTag(models.Model):
    _name = 'hrp.post_tag'
    _description = u'话题标签'

    name = fields.Char('名称')


class Partner(models.Model):
    _inherit = 'res.partner'

    post_channel_ids = fields.Many2many('hrp.post_channel', 'partner_post_channel_rel', 'partner_id', 'channel_id', '关注频道')
    post_ids = fields.Many2many('hrp.post', 'partner_post_rel', 'partner_id', 'post_id', '收藏帖子')

