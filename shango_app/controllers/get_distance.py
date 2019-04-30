# -*- encoding:utf-8 -*-
import math


class Point(object):
    pass


def max(a, b):
    if a > b:
        return a
    return b


def min(a, c):
    if a > c:
        return c
    return a


def lw(a, b, c):
    a = max(a, b)
    a = min(a, c)
    return a


def ew(a, b, c):
    while a > c:
        a -= c - b

    while a < b:
        a += c - b

    return a


def oi(a):
    return math.pi * a / 180


def Td(a, b, c, d):
    return 6370996.81 * math.acos(math.sin(c) * math.sin(d) + math.cos(c) * math.cos(d) * math.cos(b - a))


def Wv(a, b):
    if not a or not b:
        return 0
    a.lng = ew(a.lng, -180, 180)
    a.lat = lw(a.lat, -74, 74)
    b.lng = ew(b.lng, -180, 180)
    b.lat = lw(b.lat, -74, 74)
    return Td(oi(a.lng), oi(b.lng), oi(a.lat), oi(b.lat))


def get_distance(a, b):
    c = Wv(a, b)
    return c


# p1 = Point()
# p1.lat = 29.53736
# p1.lng = 106.490863
# p2 = Point()
# p2.lat = 29.537336
# p2.lng = 106.489866
#
# print getDistance(p1, p2)

