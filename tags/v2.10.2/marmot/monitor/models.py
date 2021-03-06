# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import httplib
import xmlrpclib

from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings

import redis
from redis.exceptions import ConnectionError
from rediscluster.cluster_mgt import RedisClusterMgt
from rediscluster.exceptions import RedisClusterException

from utils.node_proxy import NodeProxy
from services.models import IceServiceCenter
from .fields import PortField


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
