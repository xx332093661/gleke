# coding:utf-8
import urllib2
import json

url = 'http://192.168.0.141:8069'
# url = 'http://192.168.0.130:8069'


def http_post(url, method, data):
    url = url + method
    jdata = json.dumps(data)  # 对数据进行JSON格式化编码
    req = urllib2.Request(url, jdata)  # 生成页面请求的完整数据
    req.add_header('Content-type', 'application/json')
    response = urllib2.urlopen(req)  # 发送页面请求
    return response.read()  # 获取服务器返回的页面信息

# 设备运行
# method = '/self/start'
# data = {'code': '035', 'ip': '192.168.0.141', 'mac': 'asdgasdg1', 'version': '0.0.0.1', 'type_code': 'DCT'}

# 用户登陆
# method = '/self/user_login'
# data = {'code': '006', 'username': 'cs', 'password':  'cs'}

# 设备退出
# method = '/self/login_out'
# data = {'code': '001'}

# 获取设备信息
# method = '/self/get_equipment_info'
# data = {'code': '006'}

# 签到，叫号，未到，完成
# method = '/self/queue_state_change'
# data = {'code': '028', 'id': 6170, 'state': 1}    # id签到
# data = {'code': '001', 'outpatient_num': '1', 'state': 1}    # outpatient_num签到
# data = {'code': '001', 'outpatient_num': '2', 'state': 4}    # 叫号，未到，完成

# 上传日志
# method = '/self/logging'
# data = {'code': '001', 'log_datetime': '2016-11-24- 11:13:00', 'log_content': '测试'}

# 上传日志文件
# method = '/self/send_log'
# data = {'code': '001', 'log_file_name': 'log_test.txt', 'log_content': '测试1'}

# 获取队列
# method = '/self/get_queue'
# data = {'code': '020'}

# 心跳检查
# method = '/self/keeplive'
# data = {}

# 获取设备对应的医生信息
# method = '/self/get_empl_info_by_equip'
# data = {'code': '006'}

# 获取设备参数
# method = '/self/get_parameters'
# data = {'code': '001'}

# 获取设备广告
# method = '/self/get_ads'
# data = {'code': '001'}

# 设置设备状态
# method = '/self/set_equip_state'
# data = {'code': '006', 'state': '3'}

# 更新设备号类
# method = '/self/update_equipment_registered_types'
# data = {'code': '006', 'registered_types': ['普通']}


# 获取免费号信息
# method = '/self/get_free_num_info'
# data = {'business': '儿保'}

# 获取免费号
# method = '/self/get_free_num'
# data = {'business': '儿保', 'register_source_id': 0}

# 取消免费号
# method = '/self/cancel_free_num'
# data = {'register_source_id': 1080}

# 查询打印过的患者
# method = '/self/search_registered_patient'
# data = {'key': 's'}

# 重新打印挂号信息
# method = '/self/reprint_register_info'
# data = {'total_queue_id': 125}

# 获取医嘱
# method = '/self/get_dispose'
# data = {'partner_id': 8345, 'department_id': 1879}


# 测试
# method = '/app/test'
# data = dict()
# data['data'] = {'prev_partner_id': 3, 'current_partner_id': False, 'topic': '13562356895'}

res = http_post(url, method, data)
print res
