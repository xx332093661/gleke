# coding: utf-8
from odoo import models, api
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import random
import logging

_logger = logging.getLogger(__name__)

xing = u"赵钱孙李周吴郑王\
冯陈楮卫蒋沈韩杨\
朱秦尤许何吕施张\
孔曹严华金魏陶姜\
戚谢邹喻柏水窦章\
云苏潘葛奚范彭郎\
鲁韦昌马苗凤花方\
俞任袁柳酆鲍史唐\
费廉岑薛雷贺倪汤\
滕殷罗毕郝邬安常\
乐于时傅皮卞齐康\
伍余元卜顾孟平黄\
和穆萧尹姚邵湛汪\
祁毛禹狄米贝明臧\
计伏成戴谈宋茅庞\
熊纪舒屈项祝董梁\
杜阮蓝闽席季麻强\
贾路娄危江童颜郭\
梅盛林刁锺徐丘骆\
高夏蔡田樊胡凌霍\
虞万支柯昝管卢莫\
经房裘缪干解应宗\
丁宣贲邓郁单杭洪\
包诸左石崔吉钮龚\
程嵇邢滑裴陆荣翁\
荀羊於惠甄麹家封\
芮羿储靳汲邴糜松\
井段富巫乌焦巴弓\
牧隗山谷车侯宓蓬\
全郗班仰秋仲伊宫\
宁仇栾暴甘斜厉戎\
祖武符刘景詹束龙\
叶幸司韶郜黎蓟薄\
印宿白怀蒲邰从鄂\
索咸籍赖卓蔺屠蒙\
池乔阴郁胥能苍双\
闻莘党翟谭贡劳逄\
姬申扶堵冉宰郦雍\
郤璩桑桂濮牛寿通\
边扈燕冀郏浦尚农\
温别庄晏柴瞿阎充\
慕连茹习宦艾鱼容\
向古易慎戈廖庾终\
暨居衡步都耿满弘\
匡国文寇广禄阙东\
欧殳沃利蔚越夔隆\
师巩厍聂晁勾敖融\
冷訾辛阚那简饶空\
曾毋沙乜养鞠须丰\
巢关蒯相查后荆红\
游竺权逑盖益桓公"


class HrpTotalQueue(models.Model):
    _inherit = 'hrp.total_queue'

    def random_insert_total_queue(self):
        r1 = random.randint(1, 3)
        if r1 == 1:
            # 插入复诊数据
            self.return_visit_insert_total_queue()
        r2 = random.randint(1, 3)
        if r2 == 1:
            # 标记取报告
            self.sign_get_report()

        # 随机生成名字
        m_partner = self.env['res.partner']
        m_business = self.env['hrp.business']
        total_queue = self.env['hrp.total_queue']
        m_rule = self.env['hrp.queue_rule']

        name = ''.join(random.sample(xing, random.randint(2, 5)))
        # 是否存在
        partner = m_partner.search([('name', '=', name)])
        outpatient_num = (datetime.now() + timedelta(hours=8)).strftime('%Y%m%d%H%M%S')
        if not partner:
            # 不存在就创建
            partner = m_partner.create({'name': name, 'outpatient_num': outpatient_num, 'patient_property': 'normal'})
        # 业务类型
        businesses = m_business.search([])
        business = random.choice(businesses)
        # 科室
        if not business.business_department_ids:
            return
        business_department = random.choice(business.business_department_ids)
        department = business_department.department_id
        # 号类
        register_type = False
        if business.name == u'就诊':
            register_types = [u'普通', u'专家', u'普通', u'普通', u'普通', u'普通', u'普通', u'普通', u'普通', u'普通', u'普通', u'普通']
            register_type = random.choice(register_types)
        # 部位
        part = False
        rules = m_rule.search([('business_id', '=', business.id)])
        if rules:
            parts = []
            for line in rules[0].line_ids:
                if line.queue_field == 'part':
                    values = line.value.split(',')
                    parts += values
            if parts:
                part = random.choice(parts)
        val = {
            'partner_id': partner.id,
            'outpatient_num': outpatient_num,
            'business': business.name,
            'department_id': department.id,
            'register_type': register_type,
            'enqueue_datetime': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'is_emerg_treat': False,
            'origin': random.choice(['1', '2']),
            'state': False,
            'part': part,
            'patient_property': 'normal'
        }
        total_queue.create(val)

    def return_visit_insert_total_queue(self):
        """插入复诊数据"""
        m_queue = self.env['hrp.queue']

        his_queues = m_queue.search([('date_state', '=', 2)])
        if not his_queues:
            return
        his_queue = random.choice(his_queues)
        val = {
            'partner_id': his_queue.partner_id.id,
            'outpatient_num': his_queue.partner_id.outpatient_num,
            'business': his_queue.business,
            'department_id': his_queue.department_id.id,
            'register_type': his_queue.register_type,
            'enqueue_datetime': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'is_emerg_treat': False,
            'origin': '1',
            'state': False,
            'part': his_queue.part,
            'patient_property': 'normal'
        }

        self.create(val)

    def sign_get_report(self):
        """标记取报告"""
        qs = self.search([('business', 'in', ['CT', 'CR', 'DR']), ('state', 'not in', ['3']), ('date_state', '=', '1')], order='id')
        if qs:
            for q in qs:
                if q.queue_id.state in [4]:
                    q.state = '3'
                    break
