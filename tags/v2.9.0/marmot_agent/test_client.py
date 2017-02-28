#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import xmlrpclib


def connect_node(host, port=9001):
    return xmlrpclib.ServerProxy('http://%s:%s' % (host, port))


c = connect_node('192.168.162.91')

st = time.time()
print c.get_es_info('http://192.168.162.91:9201/_cluster/health?pretty')

print 'run time: %.1fms' % ((time.time() - st) * 1000)
