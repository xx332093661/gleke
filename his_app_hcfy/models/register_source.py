# -*- encoding:utf-8 -*-
import threading
from datetime import datetime, timedelta
import logging
from odoo import models, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

_logger = logging.getLogger(__name__)



class RegisterResource(models.Model):
    _inherit = 'his.register_source'
    register_source_lock = threading.Lock() # 号源锁




    def lock_register_source(self, register_source_id):
        """锁号源"""
        with self.register_source_lock:
            register_source = self.browse(register_source_id)

            if register_source.state == '0': # 待预约
                register_source.write({
                    'state': '2',
                    'lock_time': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                })
                return {'data': {'state': 1}} # 锁定成功

            return {'data': {'state': 0, 'msg': '号源已被占用'}} # 锁定失败


    def unlock_register_source(self, register_source_id):
        """号源解锁"""
        with self.register_source_lock:
            register_source = self.browse(register_source_id)
            if register_source.state == '2': # 锁定
                register_source.write({
                    'state': '0',
                    'lock_time': False
                })

                return {'data': {'state': 1}} # 解锁成功

            return {'data': {'state': 0, 'msg': '号源已被预约'}}  # 锁定失败



    def appointment_register(self, register_source_id):
        with self.register_source_lock:
            register_source = self.browse(register_source_id)
            if register_source.state in ['0', '2']: # 待预约、和锁定
                register_source.state = '1' # 挂号
            else:
                raise Exception(u'号源已挂号!')


    # def register_done_change_state(self, register_source_id):
    #     """挂精悍完成，修改号源状态"""
    #     with self.register_source_lock:
    #         register_source = self.browse(register_source_id)
    #         if register_source.state in ['0', '2']: # 待预约、和锁定
    #             register_source.state = '1' # 挂号
    #         else:
    #             raise Exception(u'号源已挂号!')


    @api.multi
    def unlink(self):
        # 删除队列计划
        register_plan = self.env['his.register_plan'].search([('department_id', '=', self.department_id.id), ('employee_id', '=', self.employee_id.id), ('medical_date', '=', self.date)])
        self.env['his.register_plan_line'].search([('register_plan_id', '=', register_plan.id), ('time_point_name', '=', self.time_point_name)]).unlink()
        return super(RegisterResource, self).unlink()


    @api.model
    def auto_unlock_register_source(self):
        """自动解锁号源"""
        now = datetime.now() # 当前时间
        today = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT) # 当前日期
        interval = 3 # 解锁时间间隔(分钟)
        _logger.info(u'自动解锁号源，当前日期:%s, 当前时间:%s', today, now.strftime(DEFAULT_SERVER_DATETIME_FORMAT))

        with self.register_source_lock:
            for register_resource in self.search([('state', '=', '2'), ('date', '>=', today)]):
                lock_time = register_resource.lock_time # 锁号源时间
                _logger.info(u'自动解锁号源，号源%d锁定时间:%s', register_resource, lock_time)
                if not lock_time:
                    continue

                lock_time = datetime.strptime(lock_time, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(minutes=interval)
                if lock_time < now:
                    register_resource.write({
                        'lock_time': False,
                        'state': '0'
                    })







