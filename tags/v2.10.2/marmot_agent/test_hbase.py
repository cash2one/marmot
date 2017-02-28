#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import xmlrpclib


def connect_node(host, port=9001):
    return xmlrpclib.ServerProxy('http://%s:%s' % (host, port))


c = connect_node('192.168.162.113')

st = time.time()
print c.hbase_status_simple()
print
print 'run time: %.1fms' % ((time.time() - st) * 1000)
