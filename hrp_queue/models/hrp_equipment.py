# coding: utf-8
from odoo import models, fields, api
from datetime import *
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import config
from hrp_mqtt import send_msg

import logging
import urllib2
import json

_logger = logging.getLogger(__name__)


class HrpEquipment(models.Model):
    _name = 'hrp.equipment'
    _description = u'设备'

    @api.multi
    @api.depends('user_id')
    def _get_employee(self):
        for s in self:
            s.employee_id = s.user_id.employee_ids[0].id if s.user_id and s.user_id.employee_ids else False

    name = fields.Char('设备名称')
    code = fields.Char('设备编号')
    equipment_type_id = fields.Many2one('hrp.equipment_type', '设备类型')
    ip = fields.Char('ip')
    mac = fields.Char('mac地址')
    department_info_ids = fields.One2many('hrp.department_info', 'equipment_id', '部门信息')
    equipment_parameter_ids = fields.One2many('hrp.equipment_parameter', 'equipment_id', '设备参数')
    advertisement_template_ids = fields.One2many('hrp.advertisement_template', 'equipment_id', '广告')
    log_ids = fields.One2many('hrp.equipment.log', 'equipment_id', '日志')
    version = fields.Char('版本')
    online = fields.Boolean('在线')
    user_id = fields.Many2one('res.users', '当前用户')

    business_ids = fields.Many2many('hrp.business', 'equipment_business_rel', 'equipment_id', 'business_id', '业务类型')

    queue_ids = fields.One2many('hrp.queue', 'operation_equipment_id', '接诊队列')
    floor = fields.Selection([('1', '一楼'), ('2', '二楼'), ('3', '三楼'), ('4', '四楼'), ('5', '五楼'),
                              ('6', '六楼'), ('7', '七楼'), ('8', '八楼'), ('9', '九楼')], '楼层', default='1')
    state = fields.Selection([('1', '接诊'), ('2', '暂离'), ('3', '不接诊')], '状态', default='1')

    equipment_registered_type_ids = fields.One2many('hrp.equipment_registered_type', 'equipment_id', '设备号类')

    registered_type_ids = fields.Many2many('hrp.registered.type', 'hrp_equipment_registered_type_rel', 'equipment_id',
                                           'registered_type_id', '岗位号类')

    ad_play_list_ids = fields.Many2many('hrp.ad_play_list', 'equip_ad_play_list_rel', 'equipment_id', 'list_id', '广告播放列表')
    employee_id = fields.Many2one('hr.employee', '员工', compute=_get_employee, store=1)

    _sql_constraints = [
        ('code_unique', 'unique(code)', u'设备编号不能重复'),
    ]

    @api.model
    def create(self, vals):
        code = self.env['ir.sequence'].next_by_code('hrp.equipment.code')
        vals.update({'code': code})
        return super(HrpEquipment, self).create(vals)

    # @api.onchange('registered_type_ids')
    # def onchange_registered_type(self):
    #     # 发送消息通知相关设备
    #     # 医生通知对应设备
    #     self.emplinfo_to_relation_equip(action='update_registered_type')

    def get_register_types_by_equipment(self, equipment, department_ids=False, room_ids=False, queue=None):
        """获取签到端对应部门下登陆的号类"""
        m_department_info = self.env['hrp.department_info']
        m_equipment = self.env['hrp.equipment']

        register_types = []
        # 记录在线数
        on_line_count = 0
        # 获取签到端诊室, 如果诊室为空则获取科室
        department_ids = department_ids or []
        room_ids = room_ids or []

        if equipment:
            if not department_ids:
                for department_info in equipment.department_info_ids:
                    if department_info.department_id.id not in department_ids:
                        department_ids.append(department_info.department_id.id)
            if not room_ids:
                for department_info in equipment.department_info_ids:
                    for room in department_info.room_ids:
                        if room.id not in room_ids:
                            room_ids.append(room.id)

        # 获取该诊室(科室)下登陆的号类
        args = [('equipment_id', '!=', False)]
        if room_ids:
            args += [('room_ids', 'in', room_ids)]
        elif department_ids:
            args += [('department_id', 'in', department_ids)]
        else:
            return register_types, on_line_count

        department_infos = m_department_info.search(args)

        if not department_infos:
            return register_types, on_line_count

        d_equipment_ids = [department_info.equipment_id.id for department_info in department_infos]

        equipments = m_equipment.search([('id', 'in', d_equipment_ids),
                                         ('online', '=', True),
                                         ('user_id', '!=', False),
                                         ('state', 'in', ['1', '2']),
                                         ('equipment_type_id.code', '=', 'DCT')])

        if not equipments:
            return register_types, on_line_count

        for e in equipments:

            if queue.employee_id:
                # 挂号到医生
                if e.employee_id != queue.employee_id:
                    continue

            # 叫号设备的岗位
            equip_register_types = [tp.name for tp in e.registered_type_ids]
            if queue.business in [b.name for b in e.business_ids] and e.user_id.employee_ids:
                # 队列业务类型和设备业务类型一直并且设备登陆的用户对应员工
                on_line_count += 1
                if e.user_id.employee_ids[0].registered_type_ids:
                    # 是医生或者护士并且有号类
                    for registered_type in e.user_id.employee_ids[0].registered_type_ids:
                        # 医生号类在设备号类中，不在已存在号类中
                        if registered_type.name in equip_register_types and registered_type.name not in register_types:
                            register_types.append(registered_type.name)

        return register_types, on_line_count

    def get_equipment_parameter(self):
        """计算设备参数"""
        equipment_type_parameter = {p.parameter_id.name: p.value for p in
                                    self.equipment_type_id.equipment_type_parameter_ids}
        equipment_parameter = {p.parameter_id.name: p.value for p in self.equipment_parameter_ids}
        equipment_type_parameter.update(equipment_parameter)
        return equipment_type_parameter

    def get_equipment_info_by_equipment(self):
        department_infos = self.get_department_infos_by_equipment()
        result = {
            'id': self.id,
            'equipment_name': self.name,
            'code': self.code,
            'department_infos': department_infos,
            'ip': self.ip,
            'equipment_type': self.equipment_type_id.name if self.equipment_type_id else '',
            'businesses': [business.name for business in self.business_ids],
            'employee_info': {}
        }
        # 获取登陆的医生信息
        if self.user_id.employee_ids:
            employee_info = self.get_emplp_by_equip()
            result['employee_info'].update(employee_info)
            # result['employee_info'].update({
            #     'employee_id': employee.id,
            #     'employee_name': employee.name,
            #     'image_url': '/web/image/%s/%s/image' % (employee._name, employee.id),
            #     'registered_type': [registered_type.name for registered_type in employee.registered_type_ids]
            # })
        return result

    def get_department_infos_by_equipment(self):
        """根据设备获取该设备的部门信息"""
        department_infos = []
        for department_info in self.department_info_ids:
            department_name = department_info.department_id.show_name if department_info.department_id.show_name else department_info.department_id.name
            # 获取关键字科室
            business_department = False
            for business in self.business_ids:
                for bd in business.business_department_ids:
                    if bd.department_id.id == department_info.department_id.id:
                        business_department = bd
                        break
            info = {
                'department_id': department_info.department_id.id,
                'is_write_room': business_department.is_write_room if business_department else False,
                'department_name': department_name,
                'department_pinyin': department_info.department_id.pinyin,
                'rooms': []
            }
            for room in department_info.room_ids.sorted('display_seq'):
                room_name = room.show_name if room.show_name else room.name
                info['rooms'].append({'room_id': room.id, 'room_name': room_name, 'display_seq': room.display_seq})
            department_infos.append(info)
        return department_infos

    @api.multi
    def get_client_log(self):
        equipment_ids = self.env.context['active_ids']
        if not equipment_ids:
            return

        for equipment in self.browse(equipment_ids):
            from hrp_mqtt import send_msg
            send_msg(equipment.code, {"action": "send_log"})

    @api.multi
    def equipment_restart(self):
        equipment_ids = self.env.context['active_ids']
        if not equipment_ids:
            return

        for equipment in self.browse(equipment_ids):
            from hrp_mqtt import send_msg
            send_msg(equipment.code, {"action": "restart"})

    @api.multi
    def equipment_shutdown(self):
        equipment_ids = self.env.context['active_ids']
        if not equipment_ids:
            return

        for equipment in self.browse(equipment_ids):
            from hrp_mqtt import send_msg
            send_msg(equipment.code, {"action": "shutdown"})

    def update_on_line(self):
        """监测是否在线"""
        # date_time_now = datetime.now()
        # if date_time_now.minute % 1 != 0:
        #     return

        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        url = 'http://%s:%s/api/clients' % (config['mqtt_ip'], 18083)
        password_mgr.add_password(None, url, config['mqtt_username'], config['mqtt_password'])
        handler = urllib2.HTTPBasicAuthHandler(password_mgr)

        opener = urllib2.build_opener(handler)
        res = opener.open(url)
        # urllib2.install_opener(opener)
        content = json.loads(res.read())
        clientIds = []
        for r in content['result']:
            if not r.get('clientId'):
                continue
            try:
                c = r['clientId']
                clientIds.append(c)
            except Exception:
                pass
        # 不在线的却在线的执行离线操作
        equipments_to_off = self.search([('online', '=', True), ('code', 'not in', clientIds)])

        for eoff in equipments_to_off:
            eoff.online = False
            self.env['hrp.equipment.log'].create({
                'equipment_id': eoff.id,
                'log_type': '1',
                'log_content': '设备掉线',
                'log_datetime': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            })

        # 在线的却不在线执行登陆操作
        equipments_to_on = self.search([('online', '=', False), ('code', 'in', clientIds)])
        equipments_to_on.write({'online': 1})
        for eon in equipments_to_on:
            self.env['hrp.equipment.log'].create({
                'equipment_id': eon.id,
                'log_type': '1',
                'log_content': '设备上线',
                'log_datetime': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            })

    def get_equipment_by_queue(self,  queue):
        """获取满足数据条件的叫号端"""
        if queue.employee_id.user_id:
            equipments = self.search([('user_id', '=', queue.employee_id.user_id.id), ('online', '=', True), ('state', 'in', ['1', '2']), ('equipment_type_id.code', '=', 'DCT')])
        else:
            equipments = self.search([('user_id', '!=', False), ('online', '=', True), ('state', 'in', ['1', '2']), ('equipment_type_id.code', '=', 'DCT')])
        if not equipments:
            return
        res = []
        for e in equipments:
            # 过滤不是叫号端的设备
            # if e.equipment_type_id.code not in ['DCT']:
            #     continue
            # 业务类型是否相同
            if e.business_ids:
                businesses = [business.name for business in e.business_ids]
                if queue.business not in businesses:
                    continue
            # 科室相同
            if e.department_info_ids:
                department_ids = [department_info.department_id.id for department_info in
                                  e.department_info_ids]
                if queue.department_id.id in department_ids:
                    if not queue.register_type:
                        res.append(e)
                    elif e.user_id and e.user_id.employee_ids:
                        # 号类相同
                        employee = e.user_id.employee_ids[0]
                        register_types = [reg_type.name for reg_type in employee.registered_type_ids]
                        if queue.register_type in register_types:
                            res.append(e)
        return res

    def get_room_ids_by_equipments(self, equipments):
        # 获取设备的诊室
        room_ids = []
        if not equipments:
            return room_ids
        for equipemnt in equipments:
            if not equipemnt.department_info_ids:
                return
            rooms = equipemnt.department_info_ids[0].room_ids
            rm_ids = [room.id for room in rooms]
            room_ids += rm_ids
        return room_ids

    def get_emplp_by_equip(self):
        """获取设备的员工信息"""
        if self.user_id and self.user_id.employee_ids:
            department_infos = []
            for department_info in self.department_info_ids:
                dept_info = {'department_id': department_info.department_id.id, 'room_ids': [], 'room_infos': []}
                # 诊室id，按显示顺序排序
                room_ids = department_info.room_ids.sorted('display_seq').ids
                dept_info.update({'room_ids': room_ids})
                # 诊室信息
                room_infos = []
                for room in department_info.room_ids.sorted('display_seq'):
                    room_infos.append({
                        'room_id': room.id,
                        'room_name': room.name
                    })
                dept_info.update({
                    'room_infos': room_infos
                })
                department_infos.append(dept_info)

            # 号类
            current_registered_types = []   # 当前号类
            for equipment_registered_type in self.equipment_registered_type_ids:
                if equipment_registered_type.employee_id == self.user_id.employee_ids[0]:
                    current_registered_types = [registered_type.name for registered_type in equipment_registered_type.registered_type_ids]
                    break
            registered_types = [registered_type.name for registered_type in self.user_id.employee_ids[0].registered_type_ids]   # 医生号类
            equipment_registered_types = [registered_type.name for registered_type in self.registered_type_ids]  # 设备号类
            return {
                'employee_id': self.user_id.employee_ids[0].id,
                'employee_name': self.user_id.employee_ids[0].name,
                'image_url': '/web/image/hr.employee/%s/image' % self.user_id.employee_ids[0].id,
                'registered_types': registered_types,
                'introduction': self.user_id.employee_ids[0].introduction,
                'department_infos': department_infos,
                'current_registered_types': current_registered_types,
                'equipment_registered_types': equipment_registered_types,
                'title': self.user_id.employee_ids[0].title,
            }

    def emplinfo_to_relation_equip(self, action):
        """发送医生信息到其他关联设备"""
        empl_info = self.get_emplp_by_equip()
        if empl_info and self.department_info_ids:
            for dept_ino in self.department_info_ids:
                send_msg(dept_ino.department_id.pinyin, {'action': action, 'msg': empl_info})


class HrpEquipmentType(models.Model):
    """设备类型"""
    _name = 'hrp.equipment_type'
    _description = u'设备类型'

    name = fields.Char('设备类型')
    equipment_type_parameter_ids = fields.One2many('hrp.equipment_type_parameter', 'equipment_type_id', '参数')
    code = fields.Char('类型编码')

    _sql_constraints = [
        ('code_unique', 'unique(code)', u'设备类型编号不能重复'),
    ]


class HrpEquipmentLog(models.Model):
    _name = 'hrp.equipment.log'
    _description = u'设备日志'

    @api.multi
    def _get_employee_id(self):
        for log in self:
            log.employee_id = log.user_id.employee_ids[0].id if log.user_id and log.user_id.employee_ids else False

    id = fields.Integer('ID')
    equipment_id = fields.Many2one('hrp.equipment', '设备', ondelete='cascade')
    user_id = fields.Many2one('res.users', '用户')
    log_datetime = fields.Datetime('日志时间')
    log_type = fields.Selection([('1', '后台'), ('2', '自检'), ('3', '自检报错')], '日志类型', default='1')
    log_content = fields.Char('日志内容')
    floor = fields.Selection(related='equipment_id.floor', store=1)

    _rec_name = 'equipment_id'
    _order = 'create_date desc'

    def clear_equipment_log(self):
        """清理设备日志"""
        retain_day = 30
        t = (datetime.now() - timedelta(days=retain_day)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        logs = self.search([('create_date', '<', t)])
        logs.unlink()


class HrpAdvertisement(models.Model):
    _name = 'hrp.advertisement'
    _description = u'广告'

    name = fields.Char('名称')
    image = fields.Binary('图片')
    file = fields.Binary('文件', attachment=True)
    type = fields.Selection([('image', '图片'), ('file', '文件')], '类型', default='image')


class HrpAdvertisementTemplate(models.Model):
    _name = 'hrp.advertisement_template'
    _description = u'广告模板'

    name = fields.Char('名称')
    equipment_id = fields.Many2one('hrp.equipment', '设备')
    type = fields.Selection([('1', '设备广告')], '类型', default='1')
    template_line_ids = fields.One2many('hrp.advertisement_template_line', 'template_id', '模板明细')
    interval = fields.Integer('切换时间间隔')

    @api.model
    def create(self, vals):
        """发送设备广告修改通知"""
        if vals.get('equipment_id'):
            equipment = self.env['hrp.equipment'].search([('id', '=', vals['equipment_id'])])
            if equipment:
                message = {
                    'action': 'update_ads'
                }
                send_msg(equipment.code, message)
        return super(HrpAdvertisementTemplate, self).create(vals)

    @api.multi
    def write(self, vals):
        """发送设备广告修改通知"""
        for s in self:
            if not s.equipment_id:
                continue
            message = {
                'action': 'update_ads'
            }
            send_msg(s.equipment_id.code, message)
        return super(HrpAdvertisementTemplate, self).write(vals)

    @api.multi
    def unlink(self):
        """发送设备广告修改通知"""
        for s in self:
            if not s.equipment_id:
                continue
            message = {
                'action': 'update_ads'
            }
            send_msg(s.equipment_id.code, message)
        return super(HrpAdvertisementTemplate, self).unlink()

    # @XmlrpcInterfaceWraps(
    #     funcid='1003001',
    #     model='hrp.advertisement_show_time',
    #     description=u'获取广告列表',
    #     data_format="",
    #     return_format=[])
    def get_notime_advertisement_show(self, user, employee, arg, context=None):
        """获取不定时广告"""
        m_register = user.env['hrp.equipment']
        m_show_time = user.env['hrp.advertisement_show_time']

        if not context:
            context = {}
        sender = context.get('sender')
        equipments = m_register.search([('code', '=', sender)])
        if not equipments:
            return [], 0, u'设备不存在'
        show_times = m_show_time.search([('register_id', 'in', equipments.ids)])
        if not show_times:
            return []
        results = []
        sort = 1
        for show in show_times:
            result = {
                'play_type': show.type,
                'play_time': {},
                'advers': [],
                'write_date': show.write_date
            }
            if show.type == '1':
                result['play_time'].update({'start': show.start_time, 'end': show.stop_time})
            for advertisement in show.advertisement_ids:
                result['advers'].append({
                    'adv_id': advertisement.id,
                    'adv_type': advertisement.type,
                    'url': '/web/image/%s/%s/image' % (advertisement._name, advertisement.id),
                    'text': advertisement.text,
                    'sort': sort})
                sort += 1
            results.append(result)
        return results


class HrpAdvertisementTemplateLine(models.Model):
    _name = 'hrp.advertisement_template_line'
    _description = u'广告播放模板明细'

    template_id = fields.Many2one('hrp.advertisement_template', '广告模板', ondelete='cascade')
    advertisement_id = fields.Many2one('hrp.advertisement', '广告')
    sequence = fields.Char('顺序')


class HrpAdPlayList(models.Model):
    _name = 'hrp.ad_play_list'
    _description = u'播放列表'

    name = fields.Char('名称')
    template_id = fields.Many2one('hrp.advertisement_template', '广告模板', ondelete='cascade')
    play_type = fields.Selection([('untimed', '不定时'), ('timed', '定时')], '播放类型', default='untimed')
    start = fields.Float('开始时间')
    stop = fields.Float('停止时间')



class HrpParameter(models.Model):
    """参数"""
    _name = 'hrp.parameter'
    _description = u'参数'

    name = fields.Char('参数名')
    type = fields.Selection([('equip', '设备参数')], '类型', default='equip')
    remark = fields.Char('备注')

    _rec_name = 'remark'


class HrpEquipmentTypeParameter(models.Model):
    """设备类型参数"""
    _name = 'hrp.equipment_type_parameter'
    _description = u'设备类型参数'

    equipment_type_id = fields.Many2one('hrp.equipment_type', '设备类型')
    parameter_id = fields.Many2one('hrp.parameter', '参数')
    # type = fields.Selection('类型', related='parameter_id.type')
    value = fields.Char('参数值')
    # image = fields.Binary('图片')
    remark = fields.Char('备注', related='parameter_id.remark')

    _rec_name = 'equipment_type_id'

    @api.model
    def create(self, vals):
        """发送设备参数修改通知"""
        if vals.get('equipment_type_id'):
            equipments = self.env['hrp.equipment'].search([('equipment_type_id', '=', vals['equipment_type_id']), ('online', '=', True)])
            message = {
                'action': 'update_parameters'
            }
            for equipment in equipments:
                send_msg(equipment.code, message)
        return super(HrpEquipmentTypeParameter, self).create(vals)

    @api.multi
    def write(self, vals):
        """发送设备参数修改通知"""
        message = {
            'action': 'update_parameters'
        }
        for s in self:
            if not s.equipment_type_id:
                continue
            equipments = self.env['hrp.equipment'].search([('equipment_type_id', '=', s.equipment_type_id.id), ('online', '=', True)])
            for equipment in equipments:
                send_msg(equipment.code, message)
        return super(HrpEquipmentTypeParameter, self).write(vals)

    @api.multi
    def unlink(self):
        """发送设备参数修改通知"""
        message = {
            'action': 'update_parameters'
        }
        for s in self:
            if not s.equipment_type_id:
                continue
            equipments = self.env['hrp.equipment'].search([('equipment_type_id', '=', s.equipment_type_id.id), ('online', '=', True)])
            for equipment in equipments:
                send_msg(equipment.code, message)
        return super(HrpEquipmentTypeParameter, self).unlink()


class HrpEquipmentParameter(models.Model):
    """设备参数"""
    _name = 'hrp.equipment_parameter'
    _description = u'设备参数'

    equipment_id = fields.Many2one('hrp.equipment', '设备')

    parameter_id = fields.Many2one('hrp.parameter', '参数')
    # type = fields.Selection('类型', related='parameter_id.type')
    value = fields.Char('参数值')
    # image = fields.Binary('图片')
    remark = fields.Char('备注', related='parameter_id.remark')

    @api.model
    def create(self, vals):
        """发送设备参数修改通知"""
        if vals.get('equipment_id'):
            equipment = self.env['hrp.equipment'].search([('id', '=', vals['equipment_id'])])
            if equipment:
                message = {
                    'action': 'update_parameters'
                }
                send_msg(equipment.code, message)
        return super(HrpEquipmentParameter, self).create(vals)

    @api.multi
    def write(self, vals):
        """发送设备参数修改通知"""
        for s in self:
            if not s.equipment_id:
                continue
            message = {
                'action': 'update_parameters'
            }
            send_msg(s.equipment_id.code, message)
        return super(HrpEquipmentParameter, self).write(vals)

    @api.multi
    def unlink(self):
        for s in self:
            if not s.equipment_id:
                continue
            message = {
                'action': 'update_parameters'
            }
            send_msg(s.equipment_id.code, message)
        return super(HrpEquipmentParameter, self).unlink()


class HrpDepartmentInfo(models.Model):
    """参数"""
    _name = 'hrp.department_info'
    _description = u'部门信息'

    equipment_id = fields.Many2one('hrp.equipment', '设备')
    department_id = fields.Many2one('hr.department', '科室')
    room_ids = fields.Many2many('hr.department', 'department_info_department_rel', 'department_info_id',
                                'room_id', '诊室', domain="[('parent_id', '=', department_id)]")

    # def search(self, args, offset=0, limit=None, order=None, context=None, count=False):
    #     context = context or {}
    #     department_info_ids = context.get('department_info_ids')
    #     if department_info_ids:
    #         args += [('equipment_id', 'in', [False])]
    #     return super(HrpDepartmentInfo, self).search(args, offset, limit, order, context, count)


class HrpEquipmentRigisteredType(models.Model):
    _name = 'hrp.equipment_registered_type'
    _description = u'设备号类'

    equipment_id = fields.Many2one('hrp.equipment', '设备')
    employee_id = fields.Many2one('hr.employee', '医生')
    registered_type_ids = fields.Many2many('hrp.registered.type', 'equipment_registered_type_rel', 'equipment_id',
                                           'registered_type_id', '号类')

    @staticmethod
    def is_equipment_registered_type_exit(equipment):
        """设备登陆的用户是否存在设备号类"""
        res = None
        for equipment_registered_type in equipment.equipment_registered_type_ids:
            if equipment_registered_type.employee_id and equipment_registered_type.employee_id.user_id and equipment and equipment.user_id:
                if equipment_registered_type.employee_id.user_id == equipment.user_id:
                    res = equipment_registered_type
                    break
        return res