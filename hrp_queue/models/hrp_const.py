# -*- coding: utf-8 -*-
from datetime import *
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


def time_to_client(t, time_format=DEFAULT_SERVER_DATETIME_FORMAT):
    """oe时间同步到客户端"""
    if not t:
        return
    try:
        res = (datetime.strptime(t, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=8)).strftime(time_format)
    except Exception:
        res = (datetime.strptime(t, DEFAULT_SERVER_DATETIME_FORMAT + '.%f') + timedelta(hours=8)).strftime(time_format)

    return res


def time_to_oe(t):
    """oe时间同步到客户端"""
    if not t:
        return ''
    return (datetime.strptime(t, DEFAULT_SERVER_DATETIME_FORMAT) - timedelta(hours=8)) \
        .strftime(DEFAULT_SERVER_DATETIME_FORMAT)


def date_to_client(t):
    """oe时间同步到客户端"""
    if not t:
        return ''
    return (datetime.strptime(t, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=8)).strftime(DEFAULT_SERVER_DATE_FORMAT)


def nochar(char):
    if not char:
        return ''
    return char


def noint(number):
    if not number:
        return 0
    return number


def make_list_to_sql_tuple(lists):
    if len(lists) == 1:
        tuples = '(%s)' % (lists[0])
    else:
        tuples = str(tuple(lists))
    return tuples