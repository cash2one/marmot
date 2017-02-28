#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import xmlrpclib


def connect_node(host, port=9001):
    return xmlrpclib.ServerProxy('http://%s:%s' % (host, port))


c = connect_node('127.0.0.1')

st = time.time()
print c.get_base_info()

print 'run time: %.1fms' % ((time.time() - st) * 1000)
