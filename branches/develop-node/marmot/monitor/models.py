# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import json
import urllib
import httplib
import xmlrpclib
import collections

from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings

import requests
import redis
from redis.exceptions import ConnectionError
from rediscluster.cluster_mgt import RedisClusterMgt
from rediscluster.exceptions import RedisClusterException

from utils.node_proxy import NodeProxy
from services.models import IceServiceCenter
from .fields import PortField
from .kafka import ZKKafka


class RedisClusterMonitor(models.Model):
    name = models.CharField('集群名', max_length=128)
    active = models.BooleanField('开启监控', default=False)
    note = models.TextField('备注', blank=True, default='')

    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Redis集群监控器'
        verbose_name_plural = 'Redis集群监控器列表'

    def __unicode__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        super(RedisClusterMonitor, self).__init__(*args, **kwargs)
        self._rc_mgt = None

    def modal_description(self):
        return self._meta.verbose_name

    def _create_mgt(self):
        return RedisClusterMgt(
            startup_nodes=[{'host': n.host, 'port': n.port} for n in self.redisnode_set.filter(role='Master').all()]
        )

    def get_mgt(self):
        if not self._rc_mgt:
            self._rc_mgt = self._create_mgt()
        return self._rc_mgt

    def get_info(self):
        try:
            rc = self.get_mgt()
        except RedisClusterException:
            return None
        except ConnectionError:
            return None
        else:
            return rc.info()

    def get_nodes(self):
        try:
            rc = self.get_mgt()
        except RedisClusterException:
            return None
        except ConnectionError:
            return None
        else:
            return rc.nodes()

    def get_absolute_url(self):
        return reverse('redis_cluster_detail', kwargs={'pk': self.id})

    def get_monitor_url(self):
        return reverse('redis_cluster_runtime_info', kwargs={'pk': self.id})

    def get_update_url(self):
        return reverse('redis_cluster_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('redis_cluster_delete', kwargs={'pk': self.id})


class RedisNode(models.Model):
    ROLE_CHOICES = (
        ('Master', 'Master'),
        ('Slave', 'Slave'),
    )

    cluster = models.ForeignKey(RedisClusterMonitor, verbose_name='集群')
    host = models.GenericIPAddressField('主机IP')
    port = PortField('端口')
    role = models.CharField('Master/Slave', choices=ROLE_CHOICES,  max_length=12, default='Slave')

    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Redis集群节点'
        verbose_name_plural = 'Redis集群节点列表'

    def __unicode__(self):
        return '%s:%s' % (self.host, self.port)
    
    def __init__(self, *args, **kwargs):
        super(RedisNode, self).__init__(*args, **kwargs)
        self._r = None

    def modal_description(self):
        return self._meta.verbose_name

    def get_node(self):
        return '%s:%s' % (self.host, self.port)

    def _create_redis(self):
        return redis.StrictRedis(host=self.host, port=self.port)

    def get_redis(self):
        if not self._r:
            self._r = self._create_redis()
        return self._r

    def get_info(self, section=None):
        r = self.get_redis()
        try:
            return r.info(section=section)
        except redis.ConnectionError:
            return None

    def get_absolute_url(self):
        return reverse('redis_node_detail', kwargs={'pk': self.id})

    def get_monitor_url(self):
        return reverse('redis_node_runtime_info', kwargs={'pk': self.id})

    def get_update_url(self):
        return reverse('redis_node_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('redis_node_delete', kwargs={'pk': self.id})


class ESMonitor(models.Model):
    name = models.CharField('名称', max_length=128)
    host = models.GenericIPAddressField('主机IP')
    addr = models.URLField('监控接口地址')
    active = models.BooleanField('开启监控', default=False)
    note = models.TextField('备注', blank=True, default='')

    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'ES监控器'
        verbose_name_plural = 'ES监控器列表'

    def __unicode__(self):
        return self.name

    def modal_description(self):
        return self._meta.verbose_name

    def get_state(self):
        node = NodeProxy(self.host, settings.NODE_PORT)
        try:
            return json.loads(node.get_es_info(self.addr))
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return None
        except ValueError:
            return ''

    def get_absolute_url(self):
        return reverse('es_detail', kwargs={'pk': self.id})

    def get_monitor_url(self):
        return reverse('es_runtime_info', kwargs={'pk': self.id})

    def get_update_url(self):
        return reverse('es_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('es_delete', kwargs={'pk': self.id})


class HBaseClusterMonitor(models.Model):
    name = models.CharField('集群名', max_length=128)
    host = models.GenericIPAddressField('主机')
    active = models.BooleanField('开启监控', default=False)
    note = models.TextField('备注', blank=True, default='')

    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'HBase监控'
        verbose_name_plural = 'HBase监控列表'

    def __unicode__(self):
        return self.name

    def modal_description(self):
        return self._meta.verbose_name

    def get_info(self):
        node = NodeProxy(self.host, settings.NODE_PORT)
        try:
            return node.hbase_status_simple()
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return None

    def get_absolute_url(self):
        return reverse('hbase_cluster_detail', kwargs={'pk': self.id})

    def get_monitor_url(self):
        return reverse('hbase_cluster_runtime_info', kwargs={'pk': self.id})

    def get_update_url(self):
        return reverse('hbase_cluster_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('hbase_cluster_delete', kwargs={'pk': self.id})


class Neo4jMonitor(models.Model):
    name = models.CharField('名称', max_length=128)
    host = models.GenericIPAddressField('主机IP')
    port = PortField('端口', default=7474)
    active = models.BooleanField('开启监控', default=False)
    note = models.TextField('备注', blank=True, default='')

    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Neo4j监控器'
        verbose_name_plural = 'Neo4j监控器列表'

    def __unicode__(self):
        return self.name

    def modal_description(self):
        return self._meta.verbose_name

    def get_state(self):
        """通过节点agent获取netstat -an | 7474的结果"""
        node = NodeProxy(self.host, settings.NODE_PORT)
        try:
            return node.netstat(self.port)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return None

    def get_absolute_url(self):
        return reverse('neo4j_detail', kwargs={'pk': self.id})

    def get_monitor_url(self):
        return reverse('neo4j_runtime_info', kwargs={'pk': self.id})

    def get_update_url(self):
        return reverse('neo4j_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('neo4j_delete', kwargs={'pk': self.id})


class IceGridMonitor(models.Model):
    center = models.ForeignKey(IceServiceCenter, verbose_name='注册中心')
    master = models.CharField('主注册名', max_length=32, default='Master')
    slave = models.CharField('从注册名', max_length=32, default='Replica-1')
    nodes = models.CharField('节点名(逗号分割)', max_length=64)
    active = models.BooleanField('开启监控', default=False)
    note = models.TextField('备注', blank=True, default='')

    class Meta:
        verbose_name = 'IceGrid监控器'
        verbose_name_plural = 'IceGrid监控器列表'

    def __unicode__(self):
        return self.center.name + ' - Monitor'

    def get_nodes(self):
        return self.nodes.split(',')

    def get_all_registry_names(self):
        return self.center.get_all_registry_names()

    def get_all_node_names(self):
        """在线的节点"""
        return [n['name'] for n in self.center.get_all_node_info()]


class ActiveMqMonitor(models.Model):
    name = models.CharField('名称', max_length=128)
    addr = models.URLField('监控接口地址')
    level = models.PositiveIntegerField('警报线', default=1000, help_text='队列内等待处理的消息超过这个数字就警报')
    active = models.BooleanField('开启监控', default=False)
    note = models.TextField('备注', blank=True, default='')

    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'ActiveMq监控器'
        verbose_name_plural = 'ActiveMq监控列表'

    def __unicode__(self):
        return self.name

    def modal_description(self):
        return self._meta.verbose_name

    def get_queues_info(self, pattern=re.compile(r'^org.apache.activemq:'
                                                 r'brokerName=(?P<brokerName>.*?),'
                                                 r'destinationName=(?P<destinationName>.*?),'
                                                 r'destinationType=(?P<destinationType>.*?),'
                                                 r'type=(?P<type>.*?)')):
        """pattern解析返回队列信息的key"""
        try:
            r = requests.get(self.addr)
        except requests.exceptions.ConnectionError:
            raise IOError('接口不可访问, 集群宕机!')
        if r.status_code == 404:
            raise ValueError('监控接口地址有误!')
        if r.status_code == 401:
            raise ValueError('用户名或密码错误, 无法访问!')

        queues = r.json()

        if 'value' not in queues:
            raise ValueError("接口返回的信息中没有'value'这个信息")

        info = []
        for k, v in queues['value'].items():
            match = re.search(pattern, k)
            q = collections.OrderedDict()
            q['QueueName'] = match.group('destinationName')
            q['QueueSize'] = v['QueueSize']  # Number Of Pending Messages
            q['ConsumerCount'] = v['ConsumerCount']  # Number Of Consumers
            q['EnqueueCount'] = v['EnqueueCount']  # Messages Enqueued
            q['DequeueCount'] = v['DequeueCount']  # Messages Dequeued
            info.append(q)
        return info

    def get_monitor_url(self):
        return reverse('activemq_monitor_runtime_info', kwargs={'pk': self.id})

    def get_absolute_url(self):
        return reverse('activemq_monitor_detail', kwargs={'pk': self.id})

    def get_update_url(self):
        return reverse('activemq_monitor_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('activemq_monitor_delete', kwargs={'pk': self.id})


class SpringCloudMonitor(models.Model):
    name = models.CharField('名称', max_length=128)
    addr = models.GenericIPAddressField('监控地址IP')
    port = PortField('端口')
    active = models.BooleanField('开启监控', default=False)
    note = models.TextField('备注', blank=True, default='')

    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'SpringCloud监控器'
        verbose_name_plural = 'SpringCloud监控列表'

    def __unicode__(self):
        return self.name

    def modal_description(self):
        return self._meta.verbose_name

    def ping(self):
        try:
            resp = urllib.urlopen("http://{0}:{1}/ping".format(self.addr, self.port))
            res = resp.read()
            resp.close()
        except Exception:
            return False
        return 'pong' in res

    def health(self):
        try:
            resp = urllib.urlopen("http://{0}:{1}/health".format(self.addr, self.port))
            res = resp.read()
            resp.close()
        except Exception as e:
            return str(e)
        return res

    def get_monitor_url(self):
        return reverse('springcloud_monitor_runtime_info', kwargs={'pk': self.id})

    def get_absolute_url(self):
        return reverse('springcloud_monitor_detail', kwargs={'pk': self.id})

    def get_update_url(self):
        return reverse('springcloud_monitor_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('springcloud_monitor_delete', kwargs={'pk': self.id})


class KafkaMonitor(models.Model):
    name = models.CharField('名称', max_length=128)
    addr = models.CharField('ZK集群地址', max_length=255)
    ids = models.CharField('ids', max_length=64, help_text='/brokers/ids中ids的值, 如:[2,1,0] 写作2,1,0')
    replicas = models.IntegerField('Replicas', help_text='Replicas数值个数小于此值报警')
    isr = models.IntegerField('isr', help_text='isr数值个数小于此值报警')
    active = models.BooleanField('开启监控', default=False)
    note = models.TextField('备注', blank=True, default='')

    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kafka监控器'
        verbose_name_plural = 'Kafka监控器列表'

    def __unicode__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        super(KafkaMonitor, self).__init__(*args, **kwargs)
        self.zk = None

    def create_zk(self):
        if self.zk is None:
            self.zk = ZKKafka(self.addr)
            self.zk.start()

    def destroy_zk(self):
        if self.zk:
            self.zk.stop()

    def get_ids(self):
        return self.zk.get_ids()

    def get_topics(self):
        return self.zk.get_all_topic_state()

    def get_absolute_url(self):
        return reverse('kafka_monitor_detail', kwargs={'pk': self.id})

    def get_update_url(self):
        return reverse('kafka_monitor_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('kafka_monitor_delete', kwargs={'pk': self.id})


class ZooKeeperMonitor(models.Model):
    name = models.CharField('名称', max_length=128)
    addr = models.URLField('监控接口地址')
    active = models.BooleanField('开启监控', default=False)
    note = models.TextField('备注', blank=True, default='')

    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'ZooKeeper监控器'
        verbose_name_plural = 'ZooKeeper监控列表'

    def get_monitor_url(self):
        return reverse('zookeeper_runtime_info', kwargs={'pk': self.id})

    def get_absolute_url(self):
        return reverse('zookeeper_detail', kwargs={'pk': self.id})

    def get_update_url(self):
        return reverse('zookeeper_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('zookeeper_delete', kwargs={'pk': self.id})
