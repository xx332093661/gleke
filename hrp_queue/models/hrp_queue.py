# coding:utf-8

from datetime import *
from makePinyin import pinyinAbbr
from odoo import models, api, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from hrp_const import time_to_client
from hrp_mqtt import send_msg, module


import logging
import traceback
import time
import json

_logger = logging.getLogger(__name__)

STATE = [(-1, '待排队'), (1, '待诊'), (2, '就诊中'), (3, '过号'), (4, '诊结'), (5, '退费'), (6, '取报告'), (7, '待出报告'), (8, '已取报告')]
ORIGIN = [('1', '门诊'), ('2', '住院'), ('3', '未知'), ('4', '体检'), ('5', '免费取号'), ('6', 'APP')]


class HrpTotalQueue(models.Model):
    _name = 'hrp.total_queue'
    _description = u'总排队队列'

    @api.multi
    @api.depends('partner_id')
    def _get_spell(self):
        for obj in self:
            name = obj.partner_id.name
            spells = pinyinAbbr(name, dyz=True)
            if spells:
                obj.spell = ','.join(spells)

    @api.multi
    def _get_appointment_number_str(self):
        schedule_department_employee_obj = self.env['his.schedule_department_employee']

        for s in self:
            if not s.appointment_number:
                continue
            queue_prefix = ''
            if s.employee_id:
                # 挂号到医生，医生的前缀
                schedule_department_employee = schedule_department_employee_obj.search(
                    [('department_id', '=', s.department_id.id), ('employee_id', '=', s.employee_id.id)],
                    limit=1)
                if schedule_department_employee and schedule_department_employee.queue_prefix:
                    queue_prefix = schedule_department_employee.queue_prefix
            s.appointment_number_str = '%sA%03d' % (queue_prefix, s.appointment_number)

    @api.multi
    def _compute_visit_date(self):
        for s in self:
            s.visit_date = (datetime.strptime(self.enqueue_datetime, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=8)).strftime(DEFAULT_SERVER_DATE_FORMAT)

    partner_id = fields.Many2one('res.partner', '患者')
    outpatient_num = fields.Char('门诊号')
    spell = fields.Char('姓名拼音', compute=_get_spell, store=1)
    business = fields.Char('业务类型')
    department_id = fields.Many2one('hr.department', '科室')
    room_id = fields.Many2one('hr.department', '诊室')
    employee_id = fields.Many2one('hr.employee', '挂号医生')
    visit_date = fields.Date('缴费时间', compute=_compute_visit_date)
    enqueue_datetime = fields.Datetime('入队时间', default=lambda *a: datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
    date_state = fields.Selection([('1', '有效'), ('2', '历史')], '时效', default='1')
    register_type = fields.Char('号类')
    part = fields.Char('部位')
    origin = fields.Selection(ORIGIN, '病人来源', default='1')
    state = fields.Selection([('1', '退费'), ('2', '完诊'), ('3', '取报告'), ('4', '待出报告')], '状态')
    # origin_data = fields.Char('原始数据', select=1)
    coll_method = fields.Char('采集方式')
    is_emerg_treat = fields.Boolean('急诊')
    queue_id = fields.Many2one('hrp.queue', '子队列')
    count = fields.Float('次数')

    appointment_number = fields.Integer('预约号')
    appointment_number_str = fields.Char('预约号', compute=_get_appointment_number_str)
    appointment_time = fields.Datetime('预约时间')

    operator_code = fields.Char('操作员编号')

    _order = "enqueue_datetime desc"
    _rec_name = 'partner_id'

    @api.model
    def create(self, val):
        """分诊"""
        # 分诊
        queue_id = self.dispatch(val)
        val.update({'queue_id': queue_id})

        res = super(HrpTotalQueue, self).create(val)

        # 发送挂号打印消息
        res.send_register_print_msg()

        return res

    @api.multi
    def write(self, val):
        """当修改总队列状态时，修改子队列状态并发送通知"""
        state_dict = {'1': 5, '2': 4, '3': 6, '4': 7}
        if val.get('state') and state_dict.get(val['state']):
            # 总队列状态与分诊队列状态对照
            for s in self:
                # 修改分子队列状态
                if s.queue_id:
                    # 标记状态
                    arg = {
                        'id': s.queue_id.id,
                        'state': state_dict[val['state']],
                        'code': 'oe'
                    }
                    self.env['hrp.queue'].queue_state_change(None, arg)

        return super(HrpTotalQueue, self).write(val)

    def dispatch(self, val):
        m_queue = self.env['hrp.queue']
        m_keyword = self.env['hrp.business']
        m_business_department = self.env['hrp.business_department']

        val2 = val.copy()
        val2.pop('enqueue_datetime')
        val2.pop('state')
        if val2.get('queue_id'):
            val2.pop('queue_id')

        business = m_keyword.search([('name', '=', val2['business'])])
        # 是否记录次数
        if not business or not business.record_count:
            val2.update({'count': 0})
        # 是否替换科室
        if business and business.is_replace_dept:
            if business.business_department_ids:
                val2.update({'department_id': business.business_department_ids[0].department_id.id})

        args = [('partner_id', '=', val2['partner_id']),
                ('business', '=', val2['business']),
                ('department_id', '=', val2['department_id']),
                ('register_type', '=', val2['register_type'])]

        # 挂号医生
        if val2.get('employee_id'):
            args += [('employee_id', '=', val2['employee_id'])]

        # 是否有重复数据
        args1 = args + [('date_state', '=', '1')]
        # 查询该数据的业务类型是否有组号
        if business and business.group_num:
            businesses = m_keyword.search([('group_num', '=', business.group_num)])
            business_names = [b.name for b in businesses]
            args1.remove(('business', '=', val2['business']))
            args1 += [('business', 'in', business_names)]
        # 是否有历史数据
        args2 = args + [('date_state', '=', '2')]
        queues2 = m_queue.search(args2)
        if queues2:
            if val.get('business'):
                # 查询是否启用复诊
                business_departments = m_business_department.search(
                    [('business_id.name', '=', val['business']), ('department_id', '=', val['department_id'])])
                if business_departments and business_departments[0].return_visit_enable:
                    val2.update({'return_visit': True})

        queue = m_queue.search(args1, limit=1)
        if queue:
            queue_id = queue.id
            # 优先级
            if m_keyword.search([('name', '=', queue.business)]).priority > business.priority:
                val2.update({'business': queue.business})

            if not val.get('state'):
                val2.update({
                    'enqueue_datetime': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                })
                if queue.state not in [1, 2]:
                    # 当队列状态不为待诊，就诊中时更新数据
                    # 更新状态, 更新顺序号, 更新诊室, # 更新医生, 更新入队时间
                    val2.update({
                        'stage': '1',
                        'state': -1,
                        'operation_room_id': False,
                        'operation_employee_id': False,
                        'operation_equipment_id': False,
                        'queue_dispatch_ids': [(6, 0, [])]
                    })
            elif val['state'] == '1':
                # 退费
                val2.update({'state': 5})
            elif val['state'] == '3':
                # 取报告
                val2.update({'state': 6})
            else:
                # 接诊
                val2.update({'state': 4})
            # 合并数据
            self.merge_queue(queue, val2)
            # 更新状态
            queue.write(val2)
        else:
            queue = m_queue.create(val2)
            queue_id = queue.id

        # 提交：防止签到失败回滚
        self.env.cr.commit()

        # 发送消息
        self.send_queue_msg(queue)

        # 自动签到
        m_queue.auto_sign_in(queue_id)

        # 更新就医流程
        self.env['hrp.treatment_process'].update_process(queue)

        return queue_id

    def merge_queue(self, queue, val):
        """合并队列"""
        # 合并部位
        val_part = val['part'].decode('utf-8') if val.get('part') and not isinstance(val['part'], unicode) else val.get('part')
        val_parts = val_part.split(',') if val_part else []
        queue_parts = queue.part.split(',') if queue.part else []
        if not set(val_parts).issubset(set(queue_parts)):
            new_part = ','.join(set(val_parts).union(set(queue_parts)))
            val.update({'part': new_part})

    def get_voice_format(self, queue):
        """插入发声格式"""
        context = self.env.context

        if 'voice_format' in context:
            number = ''
            patient_name = queue.partner_id.name
            department_name = ''
            room_name = ''
            business = queue.business

            if queue.department_id:
                department = queue.department_id
                department_name = department.show_name if department.show_name else department.name
            if queue.operation_room_id:
                room_name = queue.operation_room_id.show_name if queue.operation_room_id.show_name else queue.operation_room_id.name
            # 编号
            if queue.queue_dispatch_ids:
                number = queue.queue_dispatch_ids[0].order_num_str
            voice_format = {
                'n': number,
                'p': patient_name,
                'd': department_name,
                'r': room_name,
                'b': business,
            }
            try:
                voice_format = context['voice_format'] % voice_format
                return voice_format
            except Exception:
                _logger.error(u'发声格式配置错误')

    def send_queue_msg(self, queue, old_department=None):
        """发送队列消息"""
        data = self.env['hrp.queue'].clean_queue(queue)
        sub_numbers = []
        old_sub_number = self.get_sub_number_by_data(old_department)
        sub_number = self.get_sub_number_by_data(queue.department_id)
        if old_sub_number:
            sub_numbers.append(old_sub_number)
        if sub_number not in sub_numbers:
            sub_numbers.append(sub_number)
        # 插入发声格式
        voice_format = self.get_voice_format(queue)
        if voice_format:
            data.update({'voice_format': voice_format})
        message = {
            'action': 'update_queue',
            'msg': data
        }
        # 发送消息（内网）
        for s in sub_numbers:
            try:
                send_msg(s, message)
            except Exception:
                _logger.error(traceback.format_exc())
        # # 更新就医流程
        # self.env['hrp.treatment_process'].update_process(queue)
        return 1

    def get_sub_number_by_data(self, department):
        """根据数据获取订阅号"""
        if not department:
            return
        sub_number = department.pinyin if department.pinyin else '$'
        return sub_number

    def update_queue(self):
        """更新队列"""
        m_record = self.env['hrp.queue_update_record']

        start = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        date_time_now = (datetime.now() + timedelta(hours=8))
        time_now = date_time_now.time()
        date_now_str = date_time_now.date().strftime(DEFAULT_SERVER_DATE_FORMAT)
        # 当天是否更新
        records = m_record.search([('update_date', '=', date_now_str), ('state', '=', '1')])

        begin_time = datetime(1900, 1, 1, 0, 0, 1).time()
        # end_time = datetime(1900, 1, 1, h, 5, 0).time()
        # 到达开始更新队列时间
        if time_now > begin_time:
            # 当天已更新
            if records:
                return
            _logger.info('开始更新队列')

            send_msg('OdooSend', {'action': 'suspend'})

            self.clear_total_queue(date_time_now)

            self.env['hrp.queue'].clear_queue(date_time_now)

            # 记录更新记录
            m_record.create({
                'update_date': date_now_str,
                'state': '1',
                'start': start,
                'stop': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            })
            _logger.info('更新队列完成')

            send_msg('OdooSend', {'action': 'recover'})

        return

    def clear_total_queue(self, date_time_now):
        """清理总队列"""
        d = (date_time_now - timedelta(hours=date_time_now.hour, minutes=date_time_now.minute, seconds=date_time_now.second)) \
            .strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        _logger.info(u'开始修改总队列状态')
        self.env.cr.execute("update hrp_total_queue set date_state = '2' where "
                            "(enqueue_datetime + interval '8 hours') < '%s' and date_state != '2'" % d)
        self.env.cr.commit()
        _logger.info(u'修改总队列状态完成')
        # 清除历史数据
        t = (datetime.now() - timedelta(days=7)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        _logger.info(u'开始删除总队列历史数据')
        self.env.cr.execute("delete from hrp_total_queue where date_state = '2' and enqueue_datetime < '%s'" % t)
        self.env.cr.commit()
        _logger.info(u'删除总队列历史数据完成')

    @api.model
    def hrp_queue_cron(self):
        _logger.info('计划任务开始执行')
        # 测试数据
        # self.random_insert_total_queue()
        try:
            # 更新队列数据
            self.update_queue()
        except Exception:
            _logger.error(traceback.format_exc())

        try:
            # 自动签到
            self.env['hrp.queue'].auto_sign_in()
            # 自动完成
            self.env['hrp.queue'].auto_done()
            self.env.cr.commit()
        except Exception:
            self.env.cr.rollback()
            _logger.error(traceback.format_exc())

        try:
            # 检查设备运行状态
            self.env['hrp.equipment'].update_on_line()
            self.env.cr.commit()
        except Exception:
            self.env.cr.rollback()
            _logger.error(traceback.format_exc())

        try:
            # 清理设备日志
            self.env['hrp.equipment.log'].clear_equipment_log()
        except Exception:
            _logger.error(traceback.format_exc())

    def send_register_print_msg(self):
        """发送挂号打印信息"""
        equipment_obj = self.env['hrp.equipment']
        queue_obj = self.env['hrp.queue']

        # 是否是挂号
        if self.business != u'就诊':
            return

        # 没有操作员编码
        if not self.operator_code:
            return

        # 查询操作员登陆的打印设备
        equipment = equipment_obj.search([('online', '=', True), ('equipment_type_id.code', '=', 'APST'), ('employee_id.code', '=', self.operator_code)], limit=1)

        if not equipment:
            return

        gender = u'未知'
        location = self.department_id.location or ''

        # 一定挂在医生头上
        if self.employee_id:
            # 等待人数
            queues = queue_obj.search([('date_state', '=', '1'), ('department_id', '=', self.department_id.id), ('employee_id', '=', self.employee_id.id), ('state', 'in', [-1, 1, 2])])

            # 医生坐诊诊室位置
            doc_equipment = equipment_obj.search([('employee_id', '=', self.employee_id.id), ('online', '=', True)], limit=1)
            if doc_equipment and doc_equipment.department_info_ids and doc_equipment.department_info_ids[0].room_ids:
                location = doc_equipment.department_info_ids[0].room_ids[0].location or ''
        else:
            queues = queue_obj.search([('date_state', '=', '1'), ('department_id', '=', self.department_id.id), ('state', 'in', [-1, 1, 2])])

        wait_count = len(queues)

        # 平均等待时间
        average_wait_time = queue_obj.compute_average_wait_time(self.department_id.id)

        wait_time = wait_count * average_wait_time

        if self.partner_id.gender == 'male':
            gender = u'男'
        elif self.partner_id.gender == 'female':
            gender = u'女'

        # 打印的信息
        res = {
            'name': self.partner_id.name,
            'gender': gender,
            'age': self.partner_id.age or '',
            'register_time': time_to_client(self.enqueue_datetime),
            'visit_date': self.visit_date,
            'outpatient_num': self.outpatient_num or '',
            'card_no': self.partner_id.card_no or '',
            'department': self.department_id.name,
            'register_type': self.register_type or '',
            'doctor': self.employee_id.name or '',
            'doctor_title': self.employee_id.title or '',
            'location': location,
            'appointment_number': self.appointment_number_str or '',
            'wait_count': wait_count,
            'wait_time': wait_time,
        }

        message = {
            'action': 'register_print',
            'msg': res
        }
        send_msg(equipment.code, message)


class HrpQueue(models.Model):
    _name = 'hrp.queue'
    _description = u'分诊队列'

    @api.multi
    @api.depends('partner_id')
    def _get_spell(self):
        for obj in self:
            name = obj.partner_id.name
            spells = pinyinAbbr(name, dyz=True)
            if spells:
                obj.spell = ','.join(spells)

    @api.multi
    def _get_appointment_number_str(self):
        schedule_department_employee_obj = self.env['his.schedule_department_employee']

        for s in self:
            if not s.appointment_number:
                continue
            queue_prefix = ''
            if s.employee_id:
                # 挂号到医生，医生的前缀
                schedule_department_employee = schedule_department_employee_obj.search(
                    [('department_id', '=', s.department_id.id), ('employee_id', '=', s.employee_id.id)],
                    limit=1)
                if schedule_department_employee and schedule_department_employee.queue_prefix:
                    queue_prefix = schedule_department_employee.queue_prefix
            s.appointment_number_str = '%sA%03d' % (queue_prefix, s.appointment_number)

    partner_id = fields.Many2one('res.partner', '患者')
    outpatient_num = fields.Char('门诊号')
    spell = fields.Char('姓名拼音', compute=_get_spell, store=1)
    business = fields.Char('业务类型')
    department_id = fields.Many2one('hr.department', '科室')
    room_id = fields.Many2one('hr.department', '诊室')
    employee_id = fields.Many2one('hr.employee', '挂号医生')
    visit_date = fields.Date('缴费时间')
    enqueue_datetime = fields.Datetime('入队时间',
                                       default=lambda *a: datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
    register_type = fields.Char('号类')
    part = fields.Char('部位')
    origin = fields.Selection(ORIGIN, '病人来源', default='1')
    state = fields.Selection(STATE, '就诊状态', default=-1)
    coll_method = fields.Char('采集方式')
    is_emerg_treat = fields.Boolean('加急')
    stage = fields.Selection([('1', '初诊'), ('2', '回诊')], '就诊阶段', default='1')
    return_visit = fields.Boolean('复诊')
    order_num = fields.Integer('顺序号')
    write_date = fields.Datetime('修改时间')
    queue_dispatch_ids = fields.One2many('hrp.queue_dispatch', 'queue_id', '分诊')
    queue_operation_ids = fields.One2many('hrp.queue_operation', 'queue_id', '操作记录')
    date_state = fields.Selection([('1', '有效'), ('2', '历史')], '时效', default='1')
    confirm_datetime = fields.Datetime('分诊时间')

    operation_room_id = fields.Many2one('hr.department', '执行诊室')
    operation_employee_id = fields.Many2one('hr.employee', '执行医生')
    operation_time = fields.Datetime('操作时间')
    operation_equipment_id = fields.Many2one('hrp.equipment', '执行设备')

    count = fields.Float('次数', default='0')

    appointment_number = fields.Integer('预约号')
    appointment_number_str = fields.Char('预约号', compute=_get_appointment_number_str)
    appointment_time = fields.Datetime('预约时间')

    _order = "enqueue_datetime desc"
    _rec_name = 'id'

    def clean_queue(self, queue):
        if not queue:
            return
        data = {
            'id': queue.id,
            'partner_id': queue.partner_id.id,
            'name': queue.partner_id.name,
            'outpatient_num': queue.outpatient_num,
            'spell': queue.spell,
            'business': queue.business,
            'department_id': queue.department_id.id,
            'department_name': queue.department_id.name,
            'employee_id': queue.employee_id.id,
            'visit_date': queue.visit_date,
            'enqueue_datetime': time_to_client(queue.enqueue_datetime),
            'register_type': queue.register_type,
            'part': queue.part,
            'origin': queue.origin,
            'state': queue.state,
            'coll_method': queue.coll_method,
            'is_emerg_treat': queue.is_emerg_treat,
            'stage': queue.stage,
            'return_visit': queue.return_visit,
            'date_state': queue.date_state,
            'queue_dispatch_ids': [],

            'appointment_number': queue.appointment_number,
            'appointment_time': time_to_client(queue.appointment_time),
        }
        for queue_dispatch in queue.queue_dispatch_ids:
            # 计算当前等候人数
            wait_count = self.get_wait_count(queue_dispatch, data)
            data['queue_dispatch_ids'].append({
                'room_id': queue_dispatch.room_id.id,
                'room_name': queue_dispatch.room_id.name,
                'employee_ids': queue_dispatch.employee_ids.ids,
                'employee_infos': [{'employee_id': employee.id, 'employee_name': employee.name} for employee in queue_dispatch.employee_ids],
                'order_num': queue_dispatch.order_num,
                'order_num_str': queue_dispatch.order_num_str,
                'wait_count': wait_count
            })
        # 当前操作人员
        data.update({
            'operation_employee_id': queue.operation_employee_id.id,
            'operation_employee_name': queue.operation_employee_id.name,
            'operation_room_id': queue.operation_room_id.id,
            'operation_room_name': queue.operation_room_id.name,
            'operation_time': time_to_client(queue.operation_time),
        })
        return data

    def auto_sign_in(self, queue_id=False, args=None):
        """自动签到"""
        m_business_dept = self.env['hrp.business_department']
        m_queue_rule = self.env['hrp.queue_rule']

        def get_his_operation_employee(queue):
            """复诊获取历史操作医生（医生在线）"""
            his_queue = self.search([('date_state', '=', '2'),
                                     ('operation_employee_id', '!=', False),
                                     ('partner_id', '=', queue.partner_id.id),
                                     ('business', '=', queue.business),
                                     ('department_id', '=', queue.department_id.id),
                                     ('register_type', '=', queue.register_type)], order='id desc', limit=1)
            if not his_queue:
                return
            # 医生是否在线
            es = self.env['hrp.equipment'].search([('user_id', '=', his_queue.operation_employee_id.user_id.id),
                                                  ('online', '=', True), ('user_id', '!=', False), ('state', 'in', ['1', '2']), ('equipment_type_id.code', '=', 'DCT')])
            if not es:
                return
            # 当前登陆的科室是否和历史相同
            department_ids = [department_info.department_id.id for department_info in es[0].department_info_ids]
            if queue.department_id.id in department_ids:
                employee_ids.append(his_queue.operation_employee_id.id)

        time_now = datetime.now()

        args = args or [('state', 'in', [-1, 3]), ('date_state', '=', '1')]
        if queue_id:
            args += [('id', '=', queue_id)]

        queues = self.search(args, order='appointment_time, enqueue_datetime')

        if not queues:
            return
        for queue in queues:
            # 根据关键字和科室id获取关键字科室
            business_depts = m_business_dept.search([('business_id.name', '=', queue.business), ('department_id', '=', queue.department_id.id)])
            if not business_depts:
                continue
            business_dept = business_depts[0]
            # 判断是否自动签到
            is_confirm = self.queue_is_auto_confirm(time_now, queue, business_dept)
            if not is_confirm:
                continue

            room_ids = []
            employee_ids = []
            # 是否挂号到医生
            if queue.employee_id:
                employee_ids.append(queue.employee_id.id)
            else:
                # 是否是复诊
                if queue.return_visit:
                    # 分配到上次就诊的医生(医生在线)
                    get_his_operation_employee(queue)

                if not employee_ids:
                    if business_dept.is_write_room:
                        # 有调度规则
                        m_queue_rule.get_room_by_rule(queue, room_ids)
                        if not room_ids:
                            # 默认调度规则
                            # 根据数据和医生上线情况分配诊室
                            room_id = self.get_dispatch_room_id(queue)
                            if room_id:
                                room_ids.append(room_id)
            # 需要分配诊室， 却没有分配到诊室或医生，跳过
            if business_dept.is_write_room and (not room_ids and not employee_ids):
                continue

            arg = {
                'id': queue.id,
                'state': 1,
                'room_ids': room_ids,
                'employee_ids': employee_ids,
                'code': 'oe'
            }
            self.queue_state_change(None, arg)

    def sign_in(self, queue, equipment, arg, val, user=None):
        """签到"""
        m_business_dept = self.env['hrp.business_department']
        m_equipment = self.env['hrp.equipment']
        m_employee = self.env['hr.employee']

        room_ids = arg.get('room_ids', [])
        employee_ids = arg.get('employee_ids', [])
        is_emerg_treat = arg.get('is_emerg_treat', False)
        stage = arg.get('stage', False)   # 就诊阶段

        def is_employee_online(employee):
            if not employee.user_id:
                return False, u'签到失败! 医生%s未关联用户' % employee.name
            e = m_equipment.search([('user_id', '=', employee.user_id.id), ('online', '=', True), ('state', 'in', ['1', '2']), ('equipment_type_id.code', '=', 'DCT')])
            if not e:
                return False, u'签到失败! 医生%s未登陆' % employee.name
            return e[0], ''

        def get_queue_order(rm_id=None):
            """获取顺序号"""
            # 本次签到不为回诊，本身不为回诊，有预约号时返回预约号
            if (stage != '2' and queue.stage != '2') and queue.appointment_number:
                return queue.appointment_number

            # 一定条件返回之前的顺序号(当前签到不为回诊，之前有分诊信息， 状态不为-1)
            if stage != '2' and queue_dispatches and queue.state not in [-1]:
                # 1.诊室相同
                for queue_dispatch in queue_dispatches:
                    if queue_dispatch['room_id'] == rm_id:
                        return queue_dispatch['order_num']
                # 2.诊室为空， 科室不变
                if not rm_id and department.id == queue.department_id.id:
                    return queue_dispatches[0]['order_num']

            sql = '''select
            max(qd.order_num)
            from hrp_queue q
            inner
            join
            hrp_queue_dispatch qd
            on q.id = qd.queue_id
            where
            q.id != %s and q.department_id = %s and q.date_state = '1' and q.state != -1
            '''
            argu = [queue.id, department.id]

            # 回诊是否重新编号
            if business_dept.stage_new_num:
                sql += ''' and q.stage='%s' '''
                if stage:
                    # 当前有阶段以当前阶段为准
                    argu.append(stage)
                else:
                    # 当前没有阶段以队列阶段为准
                    argu.append(queue.stage)

            # 签到诊室, 并且签到要分配诊室
            if rm_id and business_dept.is_write_room:
                sql += ''' and qd.room_id=%s'''
                argu.append(rm_id)

            # 挂号到医生的
            if queue.employee_id:
                sql += ''' and q.employee_id=%s'''
                argu.append(queue.employee_id.id)

            self.env.cr.execute(sql % tuple(argu))

            o_num = self.env.cr.dictfetchall()[0]['max']
            if not o_num:
                o_num = 0
            o_num += 1
            return o_num

        def work_order_num(order_num, data, parameter):
            """加工顺序号"""
            s_count = ''
            if not order_num:
                return s_count
            # 获取签到设备参数, 看是否加了前缀
            if parameter and parameter.get('prefixes'):
                for prefix in json.loads(parameter['prefixes']):
                    if data.get(prefix['field']) == prefix['value']:
                        s_count = prefix['code']
                        break

            s_count += '%03d' % order_num
            return s_count

        def is_register_type_same(employee):
            """判断号类是否相同"""
            register_types = [register_type.name for register_type in employee.registered_type_ids]
            if queue.register_type and queue.register_type not in register_types:
                return False, u'签到医生号类不服'
            return True, ''

        def is_stage2():
            """是否回诊"""
            # 当前状态是诊结
            if queue.state == 4:
                return True

        parameter = None

        if not equipment:
            # 自动签到, 无设备
            department = queue.department_id  # 取队列的科室
        else:
            # 手动签到
            if not equipment.department_info_ids or not equipment.department_info_ids[0].department_id:
                return False, u'签到失败!设备未设置科室,请联系管理员'
            department = equipment.department_info_ids[0].department_id  # 取设备的科室
            # 获取设备参数
            parameter = equipment.get_equipment_parameter()
        if not department:
            return False, u'签到失败，科室为空，请联系管理员'

        # 根据关键字和科室id获取关键字科室
        business_depts = m_business_dept.search([('business_id.name', '=', queue.business), ('department_id', '=', department.id)])
        if not business_depts:
            return False, u'签到失败!\n%s科室下未设置%s业务\n请联系管理员' % (department.name, queue.business)
        business_dept = business_depts[0]
        # 之前的分诊信息
        queue_dispatches = []
        for dis in queue.queue_dispatch_ids:
            queue_dispatches.append({
                'room_id': dis.room_id.id,
                'order_num': dis.order_num
            })
        # 清空分诊信息,清空诊结时间,清空当前操作信息
        queue.queue_dispatch_ids.unlink()
        queue.write({
            'operation_time': False,
            'operation_room_id': False,
            'operation_employee_id': False,
            'operation_equipment_id': False,
        })

        # 是否是回诊
        if not stage:
            # 判断是否为回诊
            if is_stage2():
                stage = '2'
        if stage:
            val.update({'stage': stage})

        # 分诊医生
        if not employee_ids and queue.employee_id:
            # 未指定医生，分配到挂号医生
            employee_ids.append(queue.employee_id.id)

        queue_dispatch_ids = []
        # 是否分配诊室
        if business_dept.is_write_room:
            if room_ids:
                # 签到到诊室
                for room_id in room_ids:
                    # 获取顺序号
                    order_num = get_queue_order(room_id)
                    queue_dispatch_ids.append((0, 0, {
                        'room_id': room_id,
                        'order_num': order_num,
                    }))
            elif employee_ids:
                # 签到到医生
                # 判断医生是否在线
                employees = m_employee.search([('id', 'in', employee_ids)])
                if not employees:
                    return False, u'签到失败!指定医生不存在'
                queue_dispatch_info = {}
                for employee in employees:
                    # 判断医生号类和队列号类是否相同
                    type_same_res = is_register_type_same(employee)
                    if not type_same_res[0]:
                        return type_same_res
                    # 判断医生是否在线
                    r = is_employee_online(employee)
                    if not r[0]:
                        return r
                    employee_equip = r[0]
                    if employee_equip.department_info_ids and employee_equip.department_info_ids[0].room_ids:
                        room_id = employee_equip.department_info_ids[0].room_ids[0].id
                        if not queue_dispatch_info.get(room_id):
                            queue_dispatch_info.update({
                                room_id: [employee.id]
                            })
                        else:
                            if employee.id not in queue_dispatch_info[room_id]:
                                queue_dispatch_info[room_id].append(employee.id)
                        # room_ids.append(room_id)

                for r, e in queue_dispatch_info.items():
                    # 获取顺序号
                    order_num = get_queue_order(r)
                    queue_dispatch_ids.append((0, 0, {
                        'room_id': r,
                        'order_num': order_num,
                        'employee_ids': [(6, 0, e)]
                    }))

            else:
                if equipment:
                    # 分配到设备的诊室
                    if equipment.department_info_ids and equipment.department_info_ids[0].room_ids:
                        # 获取顺序号
                        order_num = get_queue_order(equipment.department_info_ids[0].room_ids[0].id)
                        queue_dispatch_ids.append((0, 0, {
                            'room_id': equipment.department_info_ids[0].room_ids[0].id,
                            'order_num': order_num,
                        }))
                else:
                    # 不分诊
                    return 0, u'签到失败， 没有指定到明确地点'

        else:
            # 不分诊室
            if employee_ids:
                employees = m_employee.search([('id', 'in', employee_ids)])
                if not employees:
                    return False, u'签到失败!指定医生不存在'
                for employee in employees:
                    # 判断医生号类和队列号类是否相同
                    type_same_res = is_register_type_same(employees[0])
                    if not type_same_res[0]:
                        return type_same_res
                    # 判断医生是否在线
                    r = is_employee_online(employee)
                    if not r[0]:
                        return r
            order_num = get_queue_order()

            queue_dispatch_ids.append((0, 0, {
                'order_num': order_num,
                'employee_ids': [(6, 0, employee_ids)]
            }))

        # 修改科室，并验证科室或诊室是否有对应医生坐诊
        res = self.update_queue_department(queue, equipment, department, room_ids)
        if not res[0]:
            return res[0], res[1]

        # 当前正在就诊不能签到
        if queue.state == 2:
            return False, u'正在就诊中，暂不能签到'

        # 更新签到信息
        val.update({
            'is_emerg_treat': is_emerg_treat,
            'confirm_datetime': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'queue_dispatch_ids': queue_dispatch_ids,
        })

        queue.write(val)

        # 获取返回信息提示
        desc = u"签到成功!"
        data = self.clean_queue(queue)
        for d in queue.queue_dispatch_ids:
            # 加工顺序号
            # s_order_num = work_order_num(d.order_num, data, parameter)
            # if not s_order_num:
            #     continue
            # 获取前面的候诊人数
            count = self.get_wait_count(d, data, parameter)
            # 获取返回格式
            room_name = d.room_id.name if d.room_id else queue.department_id.name
            desc += u"您的序号为%s,前面还有%s位患者" % (d.order_num_str, count)
            break

        result = {
            'name': queue.partner_id.name,
            # 'order_num': order_num,
            # 'count': count,
            'outpatient_num': queue.outpatient_num,
            'business': queue.business,
            'queue_dispatch': [{
                'room_id': nqd.room_id.id,
                'room_name': nqd.room_id.name,
                'order_num': nqd.order_num,
                'wait_count': self.get_wait_count(nqd, data, parameter)
            } for nqd in queue.queue_dispatch_ids]
        }
        return True, desc, result

    def update_queue_department(self, queue, equipment, department, room_ids):
        """签到修改科室, 并验证科室或诊室是否有对应医生坐诊"""
        m_equipment = self.env['hrp.equipment']

        old_department_id = queue.department_id.id if queue.department_id else False
        register_type = queue.register_type

        # 获取该科室和诊室下的号类
        department_ids = [department.id] if department.id else []
        register_types, on_line_count = m_equipment.get_register_types_by_equipment(equipment, department_ids, room_ids, queue=queue)
        # 没有医生在线
        if not on_line_count:
            return 0, u'签到失败,没有医生坐诊!'
        # 当数据有号类时, 判断是否有对应医生登陆
        if register_type and register_type not in register_types:
            return 0, u'签到失败,挂号类型无对应医生接诊!'
        if old_department_id != department.id:
            # 更换科室
            # queue.department_id = department.id
            # 科室不同，签到失败
            return 0, u'签到失败,请到{}就诊!'.format(queue.department_id.name)
        return 1, ''

    def update_queue_employee(self, queue, employee_ids=False):
        """更新队列的医生字段"""
        m_log = self.env['hrp.equipment.log']
        m_employee = self.pool['hr.employee']


        # 获取没个医生的诊室， 并分配
        pass

    def queue_is_auto_confirm(self, time_now, queue, business_dept):
        """该队列数据是否能自动签到"""
        if not business_dept.is_auto_confirm:
            return

        # 必须挂号到医生但没有医生不自动签到
        if business_dept.doctor_necessary and not queue.employee_id:
            return

        if queue.state == -1:
            # 判断自动时间:有预约时间，来源是APP，按预约时间自动签到，没有预约时间按入队时间自动签到，都没有，返回
            if queue.appointment_time and queue.origin == '6':
                appointment_time = datetime.strptime(queue.appointment_time, DEFAULT_SERVER_DATETIME_FORMAT)
                # 预约时间不是当天， 不自动签到
                if (appointment_time + timedelta(hours=8)).date() != (time_now + timedelta(hours=8)).date():
                    return
                # 当前时间与预约时间比较（15分钟内自动签到）
                if appointment_time - time_now < timedelta(minutes=15):
                    return True

            elif queue.enqueue_datetime:
                enqueue_time = datetime.strptime(queue.enqueue_datetime, DEFAULT_SERVER_DATETIME_FORMAT)
                # 入队时间不是当天， 不自动签到
                if (enqueue_time + timedelta(hours=8)).date() != (time_now + timedelta(hours=8)).date():
                    return
                t_e = time_now - enqueue_time
                auto_confirm_time = timedelta(minutes=(business_dept.auto_confirm_time - 0.8))
                if t_e >= auto_confirm_time:
                    return True
            else:
                return
        elif queue.state == 3:
            # 未到
            if queue.appointment_time and queue.origin == '6':
                # 有预约时间
                appointment_time = datetime.strptime(queue.appointment_time, DEFAULT_SERVER_DATETIME_FORMAT)
                # 当前时间在预约时间1分钟左右，自动签到
                t_e = time_now - appointment_time
                if timedelta(minutes=-1) <= t_e <= timedelta(minutes=1):
                    return True
            else:
                # 没有预约时间
                if business_dept.reconfirm_time:
                    # 需要过号重签
                    try:
                        write_time = datetime.strptime(queue.write_date, DEFAULT_SERVER_DATETIME_FORMAT)
                    except Exception:
                        write_time = datetime.strptime(queue.write_date, DEFAULT_SERVER_DATETIME_FORMAT + '.%f')
                    t_e = time_now - write_time
                    auto_confirm_time = timedelta(minutes=business_dept.reconfirm_time)
                    if t_e >= auto_confirm_time:
                        return True

    def get_queue_data(self, args, equipment):
        m_equipment = self.env['hrp.equipment']

        businesses = [res_business.name for res_business in equipment.business_ids]
        queues = self.search(args)
        if not queues:
            return False, u'没有您的信息,请先挂号或缴费'
        result_queue = False
        for queue in queues:
            if not result_queue:
                # 验证数据业务类型和设备业务类型是否相同
                if queue.business in businesses:
                    result_queue = queue
            # 判断数据的号类与设备对应诊室叫号端的号类是否相同
            if queue.register_type:
                # 获取签到端对应部门下登陆的号类
                register_types, on_line_count = m_equipment.get_register_types_by_equipment(equipment, queue=queue)
                if queue.register_type in register_types:
                    result_queue = queue
        if result_queue:
            return result_queue, ''
        return False, u'没有您的信息,或没有医生在线'

    def get_dispatch_room_id(self, queue):
        room_ids = self.get_dispatch_rooms(queue)
        if not room_ids:
            return
        res = {}
        # 根据可分配的诊室平均分配
        for rm_id in room_ids:
            self.env.cr.execute('''
                select count(*) from hrp_queue q inner join hrp_queue_dispatch qd on q.id=qd.queue_id where q.date_state ='1' and q.state = 1 and qd.room_id=%s
            ''' % rm_id)
            count = self.env.cr.dictfetchall()[0]['count']
            rm_id_count = room_ids.count(rm_id)
            real_count = count / rm_id_count
            res.update({rm_id: real_count})
        res = res.items()
        res.sort(key=lambda x: x[1])
        return res[0][0]

    def get_dispatch_rooms(self, queue):
        """获取可分配的诊室"""
        m_equipment = self.env['hrp.equipment']

        room_ids = []
        # 获取该科室所有满足条件的医生端
        equipments = m_equipment.get_equipment_by_queue(queue)
        if equipments:
            room_ids = m_equipment.get_room_ids_by_equipments(equipments)
        return room_ids

    def clear_queue(self, date_time_now):
        """清理队列"""
        businesses = self.env['hrp.business'].search([])

        # 删除入队时间为空的数据
        _logger.info(u'删除入队时间为空的数据')
        self.env.cr.execute("delete from hrp_queue where enqueue_datetime is null")
        self.env.cr.commit()
        _logger.info(u'删除入队时间为空的数据完成')
        # 修改包含未定义业务的数据状态
        _logger.info(u'修改包含未定义业务的数据状态')
        self.env.cr.execute("update hrp_queue set date_state='2' where "
                            "business not in (select name from hrp_business) or business is null")
        self.env.cr.commit()
        _logger.info(u'修改包含未定义业务的数据状态完成')
        # 满足条件， 置为历史
        for business in businesses:
            retain_day = business.retain_day
            d = (date_time_now - timedelta(days=(retain_day-1), hours=date_time_now.hour, minutes=date_time_now.minute, seconds=date_time_now.second))\
                .strftime(DEFAULT_SERVER_DATETIME_FORMAT)

            self.env.cr.execute("select * from hrp_queue where "
                                "((business = '%s' and count <= 0 and "
                                "((appointment_time + interval '8 hours') < '%s' or appointment_time is null)) "
                                "or state in (5)) "
                                "and date_state!='2'" % (business.name, d))
            reses = self.env.cr.dictfetchall()
            ids = [res['id'] for res in reses]
            if ids:
                _logger.info(u'%s:开始修改过期数据的状态' % business.name)
                self.search([('id', 'in', ids)]).write({'date_state': '2'})
                self.env.cr.commit()
                _logger.info(u'%s:修改过期数据的状态完成' % business.name)
        # 更新状态
        _logger.info(u'开始更新当天数据的状态')
        self.env.cr.execute("update hrp_queue set state=-1, confirm_datetime=null, operation_room_id=null, operation_employee_id=null, operation_time=null where date_state = '1'")
        self.env.cr.commit()
        _logger.info(u'更新当天数据的状态完成')

        _logger.info(u'开始删除对应分诊记录')
        self.env.cr.execute("delete from hrp_queue_dispatch where queue_id in (select id from hrp_queue where date_state = '1')")
        self.env.cr.commit()
        _logger.info(u'删除对应分诊记录完成')
        # 清除历史数据
        t = (datetime.now() - timedelta(days=7)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        _logger.info(u'开始清除子队列历史数据')
        self.env.cr.execute("delete from hrp_queue where date_state = '2' and enqueue_datetime < '%s'" % t)
        self.env.cr.commit()
        _logger.info(u'清除子队列历史数据完成')

    def queue_state_change(self, user, arg):
        """签到，叫号，过号，完成"""
        m_equipment = self.env['hrp.equipment']
        m_queue = self.env['hrp.queue']
        m_total_queue = self.env['hrp.total_queue']
        m_operation = self.env['hrp.queue_operation']
        m_queue_backup = self.env['hrp.queue_backup']

        result = {'state': 1, 'desc': u'操作成功'}
        context = {}

        code = arg.get('code')
        state = arg.get('state')
        id = arg.get('id')

        def create_queue_backup(queue):
            backup = m_queue_backup.search([('queue_id', '=', queue.id)])
            if not backup:
                self.env['hrp.queue_backup'].create({
                    'queue_id': queue.id,
                    'partner_id': queue.partner_id.id,
                    'outpatient_num': queue.outpatient_num,
                    'business': queue.business,
                    'department_id': queue.department_id.id if queue.department_id else False,
                    'room_id': queue.room_id.id if queue.room_id else False,
                    'employee_id': queue.employee_id.id if queue.employee_id else False,
                    'visit_date': queue.visit_date,
                    'enqueue_datetime': queue.enqueue_datetime,
                    'register_type': queue.register_type,
                    'part': queue.part,
                    'origin': queue.origin,
                    'coll_method': queue.coll_method,
                    'is_emerg_treat': queue.is_emerg_treat,
                    'confirm_datetime': queue.confirm_datetime,
                    'return_visit': queue.return_visit,

                    'operation_room_id': queue.operation_room_id.id if queue.operation_room_id else False,
                    'operation_employee_id': queue.operation_employee_id.id if queue.operation_employee_id else False,
                    'operation_equipment_id': queue.operation_equipment_id.id if queue.operation_equipment_id else False,
                    'operation_time': queue.operation_time,
                    'queue_operation_ids': [(0, 0, {
                        'user_id': queue.operation_employee_id.user_id.id if queue.operation_employee_id and queue.operation_employee_id.user_id else False,
                        'room_id': queue.operation_room_id.id if queue.operation_room_id else False,
                        'equipment_id': queue.operation_equipment_id.id if queue.operation_equipment_id else False,
                        'state': queue.state,
                    })]
                })
            else:
                backup.write({
                    'operation_room_id': queue.operation_room_id.id if queue.operation_room_id else False,
                    'operation_employee_id': queue.operation_employee_id.id if queue.operation_employee_id else False,
                    'operation_equipment_id': queue.operation_equipment_id.id if queue.operation_equipment_id else False,
                    'operation_time': queue.operation_time,
                    'queue_operation_ids': [(0, 0, {
                        'user_id': queue.operation_employee_id.user_id.id if queue.operation_employee_id and queue.operation_employee_id.user_id else False,
                        'room_id': queue.operation_room_id.id if queue.operation_room_id else False,
                        'equipment_id': queue.operation_equipment_id.id if queue.operation_equipment_id else False,
                        'state': queue.state,
                    })]
                })

        def msg_to_mobile(queue, state):
            # 本次操作队列
            self.env['hrp.treatment_process'].update_process(queue)

            # 如果操作为待诊，叫号，过号，诊结，退费，通知其他等候患者
            if state not in [1, 2, 3, 4, 5]:
                return

            # 通知同科室同诊室候诊者
            if not queue.queue_dispatch_ids:
                return

            qd = queue.queue_dispatch_ids[0]

            wait_queues = m_queue.search([('date_state', '=', '1'), ('id', '!=', queue.id), ('department_id', '=', queue.department_id.id), ('state', '=', 1)])

            for wait_queue in wait_queues:
                if not wait_queue.queue_dispatch_ids:
                    continue
                wqd = wait_queue.queue_dispatch_ids[0]
                if qd.room_id != wqd.room_id:
                    continue
                if qd.employee_ids.ids != wqd.employee_ids.ids:
                    continue
                if wqd.order_num <= qd.order_num:
                    continue
                # 更新就医流程
                self.env['hrp.treatment_process'].update_process(wait_queue)

            # sql = """
            #     select q.id
            #     from hrp_queue q
            #     inner
            #     join
            #     hrp_queue_dispatch qd
            #     on q.id = qd.queue_id
            #     where
            #     q.id != %s and q.department_id = %s and q.date_state = '1' and q.state = 1
            #     """
            # argu = [queue.id, queue.department_id.id]
            #
            # for dispatch in queue.queue_dispatch_ids:
            #
            #     sql2 = sql
            #
            #     if dispatch.room_id:
            #         sql2 += "and qd.room_id = %s"
            #         argu += [dispatch.room_id.id]
            #
            #     sql2 = sql2 % tuple(argu)
            #     self.env.cr.execute(sql2)
            #
            #     exe_res = self.env.cr.dictfetchall()
            #
            #     if exe_res:
            #         ids = [r['id'] for r in exe_res]
            #         wait_queues = self.browse(ids)
            #         for wait_queue in wait_queues:
            #             # 更新就医流程
            #             self.env['hrp.treatment_process'].update_process(wait_queue)

        if not id:
            outpatient_num = arg.get('outpatient_num')
            if not outpatient_num:
                return {'state': 0, 'desc': '门诊号不能为空'}
            args = [('outpatient_num', '=', outpatient_num), ('state', 'not in', [5]), ('date_state', '=', '1')]
        else:
            args = [('id', '=', id), ('date_state', '=', '1')]

        if not code:
            return {'state': 0, 'desc': u'设备编号不能为空'}

        if code in ['oe', 'app']:
            # 自动签到， 或手机签到
            # 获取唯一条数据
            queues = m_queue.search(args)
            if not queues:
                return {'state': 0, 'desc': u'未找到队列'}
            queue = queues[0]

            # 记录修改前的科室
            old_department = queue.department_id

            equipment = None
        else:
            # 获取模块
            equipment = m_equipment.search([('code', '=', code)])
            if not equipment:
                return {'state': 0, 'desc': u'设备号错误,请联系管理员'}
            # 获取唯一的一条数据
            res = m_queue.get_queue_data(args, equipment)
            if not res[0]:
                return {'state': 0, 'desc': res[1]}
            queue = res[0]

            # 记录修改前的科室
            old_department = queue.department_id

        val = {'state': state}

        if state == 1:
            # 签到(1.是否能签到 2.分配诊室)
            sign_in_res = m_queue.sign_in(queue, equipment, arg, val, user=user)
            if not sign_in_res[0]:
                # 回滚
                self.env.cr.rollback()

                return {'state': 0, 'desc': sign_in_res[1]}

            desc, res_data = sign_in_res[1], sign_in_res[2]
            result.update({'state': 1, 'desc': desc, 'res_data': res_data})

        elif state == 2:
            if not equipment:
                return {'state': 0, 'desc': u'设备号错误！'}
            # 获取叫号发声格式: 1.获取设备参数, 2, 取发声格式参数
            parameters = equipment.get_equipment_parameter()
            if 'voice_format' in parameters:
                voice_format = parameters.get('voice_format')
                context.update({'voice_format': voice_format})
        elif state == 3:
            pass
        elif state == 4:
            pass
        # if employee and state != 1:
        #     # 验证是否同一个医生操作
        #     # res = self.is_same_employee_execute(old_data, employee)
        #     # if not res:
        #     #     return [], 0, u'该患者已被其他医生处理'
        #     pass

        # 修改状态(签到是在签到方法里修改)
        if state != 1:
            queue.write(val)
        # 写入操作记录
        m_operation.create_operation(queue, state, equipment=equipment, user=user)
        # if state in [2, 4, 6, 7]:
        #     # 创建备份记录
        #     create_queue_backup(queue)
        # 提交
        self.env.cr.commit()
        # 发送消息
        m_total_queue.with_context(context).send_queue_msg(queue, old_department)
        # # 发送消息到手机
        msg_to_mobile(queue, state)

        return result

    def auto_done(self):
        """
        自动完成
        1.放射科取报告的数据
        """
        def change(args, t):
            queues = self.search(args)
            if not queues:
                return
            for queue in queues:
                write_datetime = datetime.strptime(queue.write_date, DEFAULT_SERVER_DATETIME_FORMAT)
                if datetime.now() - write_datetime < timedelta(hours=t):
                    continue
                arg = {
                    'id': queue.id,
                    'state': 8,
                    'code': 'oe'
                }

                self.queue_state_change(None, arg)

        # 门诊显示1小时，住院不显示
        change([('origin', '=', '1'), ('state', 'in', [6])], 1)
        change([('origin', '=', '2'), ('state', 'in', [6])], 0)

    def get_wait_count(self, dispatch, data, parameter=None):
        """获取前面的候诊人数"""
        business_department_obj = self.env['hrp.business_department']
        queue_dispatch_obj = self.env['hrp.queue_dispatch']

        order_num = dispatch.order_num

        department_id = data['department_id'] or 0
        employee_id = data['employee_id'] or 0
        room_id = dispatch.room_id.id

        sql = '''select count(*) from hrp_queue q inner join hrp_queue_dispatch qd
        on q.id = qd.queue_id where
        q.department_id = %s and
        q.date_state = '1' and
        q.state = 1 and
        qd.order_num < %s'''

        argu = [department_id, order_num]

        # 诊室
        if room_id:
            sql += " and qd.room_id = %s"
            argu += [room_id]

        # 医生
        if employee_id:
            sql += " and q.employee_id = %s"
            argu += [employee_id]

        # 另一阶段等候人数
        another_wait_count = 0

        # 就诊阶段
        # 回诊是否重新签到
        business_department = business_department_obj.search([('business_id.name', '=', data['business']), ('department_id', '=', department_id)], limit=1)
        if business_department and business_department.stage_new_num:
            sql += " and q.stage = '%s'"
            argu += [data['stage']]

            # 另一阶段的等候人数
            another_stage = '2' if data['stage'] == '1' else '1'

            another_args = [('queue_id.date_state', '=', '1'), ('queue_id.department_id', '=', department_id), ('queue_id.stage', '=', another_stage), ('queue_id.state', '=', 1)]

            if room_id:
                another_args += [('room_id', '=', room_id)]

            if employee_id:
                another_args += [('queue_id.employee_id', '=', employee_id)]
            queue_dispatches = queue_dispatch_obj.search(another_args)
            another_wait_count = len(queue_dispatches)

        self.env.cr.execute(sql % tuple(argu))

        res = self.env.cr.dictfetchall()[0]['count']

        if not res:
            res = 0

        # 增加另一阶段的等候人数
        if another_wait_count:
            if another_wait_count <= res:
                res += another_wait_count
            else:
                res += res

                # 判断该队列当前叫号的阶段
                called_args = [('queue_id.date_state', '=', '1'), ('queue_id.department_id', '=', department_id), ('queue_id.state', '=', 2)]
                if room_id:
                    called_args += [('room_id', '=', room_id)]

                if employee_id:
                    called_args += [('queue_id.employee_id', '=', employee_id)]

                # 下次叫号，默认叫初诊
                next_called_stage = '1'

                current_called = queue_dispatch_obj.search(called_args, limit=1)
                if current_called:
                    next_called_stage = '2' if current_called.queue_id.stage == '1' else '1'

                if next_called_stage != data['stage']:
                    res += 1
        return res

    def compute_average_wait_time(self, department_id):
        """计算平均等待时间"""
        queue_obj = self.env['hrp.queue']
        queue_operation_obj = self.env['hrp.queue_operation']

        wait_time = 3

        # 查询最近5次的平均时间
        done_queues = queue_obj.search([('department_id', '=', department_id), ('state', '=', '4')], order='operation_time desc', limit=5)

        durations = []

        for done_queue in done_queues:
            # 查询叫号到完成的时间间隔
            # 最近一次叫号
            qo = queue_operation_obj.search([('queue_id', '=', done_queue.id),
                                             ('state', '=', '2'),
                                             ('create_date', '<', done_queue.operation_time)], order='create_date desc', limit=1)
            if not qo:
                continue

            done_operation_time = datetime.strptime(done_queue.operation_time, DEFAULT_SERVER_DATETIME_FORMAT)
            qo_operation_time = datetime.strptime(qo.create_date, DEFAULT_SERVER_DATETIME_FORMAT)

            duration = (done_operation_time - qo_operation_time).seconds / 60

            durations.append(duration)

        if durations:
            # 计算平均值
            wait_time = sum(durations)/len(durations)

        if wait_time > 5:
            wait_time = 3

        return wait_time


class HrpQueueDispatch(models.Model):
    _name = 'hrp.queue_dispatch'
    _description = u'分诊'

    @api.multi
    @api.depends('queue_id.state')
    def _get_state_str(self):
        for s in self:
            s.state_str = dict(STATE)[int(s.queue_id.state)]

    @api.multi
    def _get_order_num_str(self):
        schedule_department_employee_obj = self.env['his.schedule_department_employee']

        for s in self:
            queue_prefix = ''
            if s.queue_id.employee_id:
                # 挂号到医生，医生的前缀
                schedule_department_employee = schedule_department_employee_obj.search([('department_id', '=', s.department_id.id), ('employee_id', '=', s.queue_id.employee_id.id)], limit=1)
                if schedule_department_employee and schedule_department_employee.queue_prefix:
                    queue_prefix = schedule_department_employee.queue_prefix
            if s.stage == '1':
                # 初诊
                s.order_num_str = '%sA%03d' % (queue_prefix, s.order_num)
            else:
                # 回诊
                s.order_num_str = '%sB%03d' % (queue_prefix, s.order_num)

    queue_id = fields.Many2one('hrp.queue', '队列', ondelete='cascade')
    business = fields.Char(related='queue_id.business', store=1)
    department_id = fields.Many2one('hr.department', related='queue_id.department_id', store=1)
    partner_id = fields.Many2one('res.partner', related='queue_id.partner_id', store=1)
    room_id = fields.Many2one('hr.department', '分诊诊室')
    employee_ids = fields.Many2many('hr.employee', 'dispatch_employee_rel', 'dispatch_id', 'employee_id', '分诊医生')
    order_num = fields.Integer('顺序号')

    date_state = fields.Selection(related='queue_id.date_state', store=1)
    enqueue_datetime = fields.Datetime(related='queue_id.enqueue_datetime')
    confirm_datetime = fields.Datetime(related='queue_id.confirm_datetime')
    stage = fields.Selection(related='queue_id.stage')
    state_str = fields.Char('就诊状态', compute=_get_state_str, store=1)
    order_num_str = fields.Char('顺序号', compute=_get_order_num_str)

    _rec_name = 'id'


class HrpQueueOperation(models.Model):
    _name = 'hrp.queue_operation'
    _description = u'队列操作'

    queue_id = fields.Many2one('hrp.queue', '队列', ondelete='cascade')
    user_id = fields.Many2one('res.users', '操作人员')
    room_id = fields.Many2one('hr.department', '诊室')
    equipment_id = fields.Many2one('hrp.equipment', '设备')
    state = fields.Selection(STATE, '操作状态')
    create_date = fields.Datetime('操作时间')

    def create_operation(self, queue, state, equipment=None, user=None):
        room_id = equipment.department_info_ids[0].room_ids[0].id if equipment and equipment.department_info_ids and equipment.department_info_ids[0].room_ids else False
        equipment_id = equipment.id if equipment else False
        self.create({
            'queue_id': queue.id,
            'user_id': user.id if user else False,
            'room_id': room_id,
            'state': state,
            'equipment_id': equipment_id
        })
        queue_val = {
            'operation_time': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        }
        if state == 2:
            # 当为叫号状态，在队列中记录
            if room_id:
                queue_val.update({'operation_room_id': room_id})
            if user and user.employee_ids:
                queue_val.update({'operation_employee_id': user.employee_ids[0].id})
            if equipment:
                queue_val.update({'operation_equipment_id': equipment_id})
        queue.write(queue_val)


class HrpQueueUpdateRecord(models.Model):
    _name = 'hrp.queue_update_record'
    _description = u'队列更新记录'

    update_date = fields.Date('更新日期')
    state = fields.Selection([('0', '未更新'), ('1', '已更新')], '状态')
    start = fields.Datetime('开始时间')
    stop = fields.Datetime('完成时间')

    _rec_name = 'update_date'
    _order = 'start desc'


class HrpTotalQueueBackup(models.Model):
    _name = 'hrp.total_queue_backup'
    _description = u'队列数据备份'

    @api.model
    def _get_spell(self):
        for obj in self:
            name = obj.partner_id.name
            spells = pinyinAbbr(name, dyz=True)
            if spells:
                obj.spell = ','.join(spells)

    partner_id = fields.Many2one('res.partner', '患者')
    outpatient_num = fields.Char('门诊号')
    spell = fields.Char('姓名拼音', compute=_get_spell, store=1)
    business = fields.Char('业务类型')
    department_id = fields.Many2one('hr.department', '挂号科室')
    room_id = fields.Many2one('hr.department', '挂号诊室')
    employee_id = fields.Many2one('hr.employee', '挂号医生')
    visit_date = fields.Date('缴费时间')
    enqueue_datetime = fields.Datetime('入队时间', default=lambda *a: datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
    register_type = fields.Char('号类')
    part = fields.Char('部位')
    origin = fields.Selection(ORIGIN, '来源', default='1')
    state = fields.Selection([('1', '退费'), ('2', '完诊'), ('3', '取报告')], '状态')
    coll_method = fields.Char('采集方式')
    is_emerg_treat = fields.Boolean('加急')

    _order = "enqueue_datetime desc"
    _rec_name = 'partner_id'


class HrpQueueBackup(models.Model):
    _name = 'hrp.queue_backup'
    _description = u'队列备份'

    @api.multi
    @api.depends('partner_id')
    def _get_spell(self):
        for obj in self:
            name = obj.partner_id.name
            spells = pinyinAbbr(name, dyz=True)
            if spells:
                obj.spell = ','.join(spells)

    @api.multi
    @api.depends('operation_time')
    def _get_operation_date(self):
        for s in self:
            if s.operation_time:
                s.operation_date = (datetime.strptime(s.operation_time, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=8)).strftime(DEFAULT_SERVER_DATE_FORMAT)

    partner_id = fields.Many2one('res.partner', '患者')
    outpatient_num = fields.Char('门诊号')
    spell = fields.Char('姓名拼音', compute=_get_spell, store=1)
    business = fields.Char('业务类型')
    department_id = fields.Many2one('hr.department', '科室')
    room_id = fields.Many2one('hr.department', '诊室')
    employee_id = fields.Many2one('hr.employee', '挂号医生')
    visit_date = fields.Date('缴费时间')
    enqueue_datetime = fields.Datetime('入队时间')
    register_type = fields.Char('号类')
    part = fields.Char('部位')
    origin = fields.Selection(ORIGIN, '来源', default='1')
    coll_method = fields.Char('采集方式')
    is_emerg_treat = fields.Boolean('加急')
    confirm_datetime = fields.Datetime('分诊时间')
    return_visit = fields.Boolean('复诊')

    operation_room_id = fields.Many2one('hr.department', '执行诊室')
    operation_employee_id = fields.Many2one('hr.employee', '执行医生')
    operation_time = fields.Datetime('诊结时间')
    operation_equipment_id = fields.Many2one('hrp.equipment', '执行设备')

    operation_date = fields.Date('诊结日期', compute=_get_operation_date, store=1)

    queue_id = fields.Many2one('hrp.queue', '队列')

    queue_operation_ids = fields.One2many('hrp.queue_operation_backup', 'queue_id', '操作记录')

    _order = "operation_time desc"
    _rec_name = 'id'


class HrpQueueOperationBackup(models.Model):
    _name = 'hrp.queue_operation_backup'
    _description = u'操作'

    queue_id = fields.Many2one('hrp.queue_backup', '队列', ondelete='cascade')
    user_id = fields.Many2one('res.users', '操作人员')
    room_id = fields.Many2one('hr.department', '诊室')
    equipment_id = fields.Many2one('hrp.equipment', '设备')
    state = fields.Selection(STATE, '操作状态')
    create_date = fields.Datetime('操作时间')