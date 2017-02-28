#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import socket
import fcntl
import struct
import xmlrpclib

import redis


# RDS = redis.StrictRedis(host='localhost', port=6379, db=0)
#
# print RDS.get('123')


def connect_node(host, port=9001):
    return xmlrpclib.ServerProxy('http://%s:%s' % (host, port))

# c = connect_node('localhost')
#
# st = time.time()
#
# # print c.start_monitor()
# # print c.stop_monitor()
#
# print c.get_base_info()
#
# print 'run time: %.1fms' % ((time.time()-st)*1000)


c = connect_node('localhost')

st = time.time()
# print c.start_monitor()
# print c.stop_monitor()
print c.get_base_info()
print
print 'run time: %.1fms' % ((time.time()-st)*1000)

c.close()


# def get_local_ip_(ifname='eth0'):
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     # 0x8915 -- SIOCGIFADDR
#     return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])
