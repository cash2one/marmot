#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import pprint
import requests


# pattern = re.compile(
#     r'^org.apache.activemq:'
#     r'brokerName=(?P<brokerName>.*?),'
#     r'destinationName=(?P<destinationName>.*?),'
#     r'destinationType=(?P<destinationType>.*?),'
#     r'type=(?P<type>.*?)$'
# )
#
# try:
#     r = requests.get('http://admin:admin@192.168.162.238/api/jolokia/read/org.apache.activemq:brokerName=amq-B,type=Broker,destinationType=Queue,destinationName=*/')
# except requests.exceptions.ConnectionError:
#     raise
#
# print r.status_code
# queues = r.json()
# for k, v in queues['value'].items():
#     match = re.search(pattern, k)
#     print 'brokerName: ', match.group('brokerName')
#     print 'destinationName: ', match.group('destinationName')
#     print 'destinationType: ', match.group('destinationType')
#     print 'type: ', match.group('type')
#     print '--------------------------------------------------'
#     print 'Number Of Pending Messages: ', v['QueueSize']
#     print 'Number Of Consumers: ',v['ConsumerCount']
#     print 'Messages Enqueued: ',v['EnqueueCount']
#     print 'Messages Dequeued: ',v['DequeueCount']

    # QueueSize: Number Of Pending Messages
    # ConsumerCount: Number Of Consumers
    # EnqueueCount:  Messages Enqueued
    # DequeueCount: Messages Dequeued


# 从es读取历史数据
addr = 'http://logstash.100credit.cn/elasticsearch/[索引名]/[type]/_search?q=[查询字符串]'

r = requests.get('http://logstash.100credit.cn/elasticsearch/activemq-*/Queue/_search?q=@timestamp:[now-1m TO now] AND fields.broker_name:amq-A')
print r.status_code
pprint.pprint(r.json())


if __name__ == '__main__':
    pass
