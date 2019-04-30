# coding:utf-8
import urllib2
import json

url = 'http://121.201.68.100:8069'
# url = 'http://192.168.0.141:8069'


def http_post(url, method, data):
    url = url + method
    jdata = json.dumps(data)  # 对数据进行JSON格式化编码
    req = urllib2.Request(url, jdata)  # 生成页面请求的完整数据
    req.add_header('Content-type', 'application/json')
    response = urllib2.urlopen(req)  # 发送页面请求
    return response.read()  # 获取服务器返回的页面信息

mac = '2db15a5e-55ca-11e7-98f3-52542a7f464e'
token = 'l7xh6eCRj40Q'


# mac = '663015cf-4f1e-11e7-99c1-005056c00008'
# token = 'oD7lNCH8'

data = {'token': token, 'mac': mac}

# app运行
# method = '/app/start'
# data = {'mac': mac, 'coordinate': {'longitude': 0, 'latitude': 0}, 'data': {'company_id': ''}, 'company_id': 0}

# app运行（外部）
# method = '/app/startapp'
# data = {'coordinate': {'longitude': 0, 'latitude': 0}, 'company_id': 0}

# 获取科室
# method = '/app/get_departments'
# data['data'] = {'company_id': 1}

# 获取科室下的医生
# method = '/app/get_doctors2'
# data['data'] = {'department_id': 7756}

# 获取科室下的医生
# method = '/app/get_shift'
# data['data'] = {'department_id': 7249, 'employee_id': 14320}

# 获取根据排班获取号源
# method = '/app/get_register_sources'
# data['data'] = {'department_id': 5840, 'employee_id': 10635}

# 获取班次号源
# method = '/app/get_shift_register_sources'
# data['data'] = {'shift_id': 2091}

# 获取验证码
# method = '/app/get_verify_code'
# data['data'] = {'phone': '13100000000'}

# 用户注册
# method = '/app/register'
# data['data'] = {'phone': '13100000000', 'password': '123', 'verify_code': '533934'}

# 用户登陆
# method = '/app/login'
# data['data'] = {'phone': '13100000000', 'password': '123'}
# data['data'] = {'phone': '13509474140', 'password': '123456789'}

# 忘记密码
# method = '/app/forget_password'
# data['data'] = {'phone': '13100000000', 'password': '123', 'verify_code': 632507}

# 修改密码
# method = '/app/change_password'
# data['data'] = {'partner_id': 8, 'old_password': '123', 'new_password': '321'}

# 修改用户信息
# method = '/app/change_partner_info'
# data['data'] = {'partner_id': 8, 'name': '张胜男'}

# 查询客户
# method = '/app/search_partner'
# data['data'] = {'phone': '15000000000'}

# 关联联系人
# method = '/app/add_relationship'
# data['data'] = {'partner_id': 28, 'relations': [{'partner_id': 46, 'relationship': 'son'}]}

# 添加患者
# method = '/app/add_patient'
# data['data'] = {'partner_id': 28, 'relationship': 'daughter', 'name': '28-1', 'patient_property': 'newborn', 'sex': 'male', 'inoculation_code': '123456', 'birth_date': '2017-3-1', 'plan_born_day': '2018-3-1'}

# 挂号确认支付
# method = '/app/register_confirm_pay'
# data['data'] = {'partner_id': 809, 'user_id': 809, 'register_source_id': 65109, 'pay_method': 'long'}


# 确认充值
method = '/app/recharge_confirm_pay'
data['data'] = {'user_id': 809, 'partner_id': 809, 'company_id': 14, 'pay_method': 'longpay', 'amount': 0.01, 'recharge_type': '1'}

# 查询订单支付结果
# method = '/app/get_order_pay_state'
# data['data'] = {'order_id': 389}

# 当前接种
# method = '/app/current_inoculation'
# data['data'] = {'partner_id': 8}

# 接种计划和接种记录
# method = '/app/inoculation_schedule_and_record'
# data['data'] = {'partner_id': 39, 'cycle_id': 17}  # 9 39

# 接种预约
# method = '/app/inoculation_appointment'
# data['data'] = {'company_id': 7}

# 接种预约确认支付
# method = '/app/inoculation_confirm_pay'
# data['data'] = {'partner_id': 39, 'register_source_id': 19145, 'pay_method': 'weixin', 'inoculation_schedules': [{'cycle_id': 17, 'item_ids': [1]}]}

# 当前孕产
# method = '/app/current_pregnant'
# data['data'] = {'partner_id': 12, 'current_date': '2017-06-14'}

# 产检详情
# method = '/app/pregnant_inspection'
# data['data'] = {'pregnant_inspection_id': 1}

# 产检记录
# method = '/app/pregnant_inspection_record'
# data['data'] = {'partner_id': 10}

# 全部产检
# method = '/app/all_pregnant_inspection'
# data['data'] = {'partner_id': 12}

# 当前儿保
# method = '/app/current_child_health'
# data['data'] = {'partner_id': 11, 'current_date': '2017-3-10'}

# 儿保预约
# method = '/app/child_health_appointment'
# data['data'] = {'partner_id': 11, 'inspection_id': 1}

# 便民门诊
# method = '/app/convenience'
# data['data'] = {'company_id': 10}

# 便民门诊项目详情(外网)
# method = '/app/convenience_item'
# data['data'] = {'item_id': 1}

# 便民门诊确认下单
# method = '/app/convenience_confirm_order'
# data['data'] = {'item_id': 3}

# 获取频道分类
# method = '/app/get_post_channel_category'
# data['data'] = {'page': 1}

# 获取话题标签
# method = '/app/get_post_tag'
# data['data'] = {}

# 获取频道
# method = '/app/get_post_channel'
# data['data'] = {'page': 1, 'category_id': 3}

# 获取我的频道
# method = '/app/get_my_post_channel'
# data['data'] = {'page': 1, 'partner_id': 3}

# 获取话题
# method = '/app/get_post'
# data['data'] = {'page': 1, 'channel_id': 1}

# 获取话题内容
# method = '/app/get_post_content'
# data['data'] = {'page': 1, 'post_id': 1}

# 创建话题
# method = '/app/create_post'
# data['data'] = {'channel_id': 1, 'title': '111', 'partner_id': 1, 'content': '速度快老规矩', 'tag_ids': [1,2]}

# 发表内容
# method = '/app/create_post_content'
# data['data'] = {'post_id': 11, 'partner_id': 1, 'content': '测试111', 'images': []}

# 关注频道
# method = '/app/follow_channel'
# data['data'] = {'channel_id': 1, 'partner_id': 1}

# 取消关注频道
# method = '/app/cancel_follow_channel'
# data['data'] = {'channel_id': 1, 'partner_id': 1}

# 获取关注频道
# method = '/app/get_follow_channel'
# data['data'] = {'partner_id': 1}

# 收藏话题
# method = '/app/collect_post'
# data['data'] = {'post_id': 1, 'partner_id': 1}

# 取消收藏话题
# method = '/app/cancel_collect_post'
# data['data'] = {'post_id': 1, 'partner_id': 1}

# 获取关注频道
# method = '/app/get_collect_post'
# data['data'] = {'partner_id': 1}

# 新闻

# 获取新闻频道分类
# method = '/app/get_news_channel_category'
# data['data'] = {'page': 1}

# 获取新闻频道
# method = '/app/get_news_channel'
# data['data'] = {'page': 1, 'category_id': 3}

# 获取新闻话题
# method = '/app/get_news_post'
# data['data'] = {'page': 1, 'channel_id': 3}

# 获取新闻内容
# method = '/app/get_news_content'
# data['data'] = {'post_id': 11}

# 获取新闻内容
# method = '/app/get_news_comment'
# data['data'] = {'post_id': 11}

# 发表新闻评论
# method = '/app/create_news_comment'
# data['data'] = {'post_id': 11, 'partner_id': 1, 'content': '测试111', 'images': []}

res = http_post(url, method, data)
print res


