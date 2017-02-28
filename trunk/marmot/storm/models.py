# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import uuid
import os
import time
import urlparse
import hashlib
import xmlrpclib
import httplib

from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings

from utils.node_proxy import NodeProxy
from assets.models import Server


class StormCluster(models.Model):
    
    name = models.CharField(max_length=48, verbose_name='名称')
    note = models.TextField(verbose_name='描述', blank=True, default='')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'StormCluster'
        verbose_name_plural = 'StormClusters'
        permissions = {
            ('operate_storm_node', "start stop storm-node"),
            ('push_storm_jar_pkg', "push storm jar package"),
            ('run_storm_jar_pkg', "run storm jar package"),
        }

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('storm_cluster_detail', args=[self.pk])

    def get_update_url(self):
        return reverse('storm_cluster_update', args=[self.pk])

    def get_delete_url(self):
        return reverse('storm_cluster_delete', args=[self.pk])


class StormNode(models.Model):
    NODE_TYPE = (
        ('nimbus', 'Nimbus'),
        ('supervisor', 'Supervisor'),
        ('ui', 'UI')
    )

    name = models.CharField(max_length=48, verbose_name='名称')
    host = models.ForeignKey(Server, verbose_name='主机', blank=True, default='')
    type = models.TextField(verbose_name='类型', blank=True, choices=NODE_TYPE)
    note = models.TextField(verbose_name='描述', blank=True, default='')
    cluster = models.ForeignKey(StormCluster,verbose_name='storm集群', blank=True, default='')
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Storm节点'
        verbose_name_plural = 'Storm节点列表'

    def __unicode__(self):
        return self.name

    def kill(self):
        node = NodeProxy(self.host.ip, settings.NODE_PORT)
        try:
            return node.kill_storm(self.type)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return False

    def start(self):
        node = NodeProxy(self.host.ip, settings.NODE_PORT)
        try:
            return node.start_storm(self.type)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return False

    def is_alive(self):
        node = NodeProxy(self.host.ip, settings.NODE_PORT)
        try:
            return node.storm_is_alive(self.type)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return False

    def restart(self):
        node = NodeProxy(self.host.ip, settings.NODE_PORT)
        node.kill_storm(self.type)
        time.sleep(0.1)
        node.start_tomcat(self.type)

    def get_absolute_url(self):
        return reverse('storm_node_detail', args=[self.pk])

    def get_update_url(self):
        return reverse('storm_node_update', args=[self.pk])

    def get_delete_url(self):
        return reverse('storm_node_delete', args=[self.pk])
    

class StormApp(models.Model):
    cluster = models.ForeignKey(StormCluster,verbose_name='storm集群', blank=True, default='')
    name = models.CharField(max_length=48, verbose_name='名称')
    note = models.TextField(blank=True, default='', verbose_name='描述')
    main_function = models.CharField(max_length=48, verbose_name='主函数')
    args = models.CharField(max_length=48, verbose_name='运行参数')
    user = models.ManyToManyField(User, blank=True, verbose_name='开发者')
    identifier = models.UUIDField(default=uuid.uuid4, editable=False, verbose_name='标识')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Storm应用'
        verbose_name_plural = 'Storm应用列表'
        unique_together = (('cluster', 'name'),)
        
    def __unicode__(self):
        return '{0} - {1}'.format(self.name, self.cluster.name)
    
    @classmethod
    def type(cls):
        return 'storm'
    
    @property
    def hex_identifier(self):
        return self.identifier.get_hex()
    
    def get_users_display(self):
        return '; '.join([user.get_full_name() for user in self.user.all()])

    def get_active_jar(self):
        return self.stormappjar_set.filter(active=True).first()
    
    def push_jar(self, jar, storm_app_node, priority=1):
        task = {
            'type': 'storm_jar',
            'host': storm_app_node.node.host.ip,
            'app_name': self.name,
            'identifier': self.hex_identifier,
            'priority': priority,
            'jar_dir': storm_app_node.jar_dir.jar_dir,
            'jar_url': jar.get_download_url(),
            'jar_md5': jar.md5,
        }
        node = NodeProxy(storm_app_node.node.host.ip, settings.NODE_PORT)
        return node.add_task(task)
    
    def run_jar(self, jar, storm_app_node, storm_app, priority=1):
        task = {
            'type': 'run_storm_jar',
            'host': storm_app_node.node.host.ip,
            'app_name': self.name,
            'identifier': self.hex_identifier,
            'priority': priority,
            'jar_dir': storm_app_node.jar_dir.jar_dir,
            'jar_url': jar.get_download_url(),
            'jar_md5': jar.md5,
            'jar_main_function':storm_app.main_function,
            'jar_args':storm_app.args,
        }
        node = NodeProxy(storm_app_node.node.host.ip, settings.NODE_PORT)
        return node.add_task(task)
 
    def check_jar(self, jar, storm_app_node):
        node = NodeProxy(storm_app_node.node.host.ip, settings.NODE_PORT)
        jar_path = '%s/%s.jar'%(storm_app_node.jar_dir.jar_dir,self.name)
        jar_md5 = jar.md5
        try:
            return node.check_storm_jar(jar_path,jar_md5)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return False
    
    def get_absolute_url(self):
        return reverse('storm_app_detail', args=[self.pk])

    def get_update_url(self):
        return reverse('storm_app_update', args=[self.pk])

    def get_delete_url(self):
        return reverse('storm_app_delete', args=[self.pk])

   
class StormAppJar(models.Model): 
    STATE_CHOICES = (
        (1, '下载中'),
        (2, '就绪'),
        (3, '下载失败'),
    )
    url = models.URLField(verbose_name='jar包地址')
    package = models.FileField(upload_to='storm_apps/jar/', blank=True, null=True)
    state = models.IntegerField(verbose_name='状态', choices=STATE_CHOICES, default=1)
    note = models.TextField(verbose_name='描述', blank=True, default='')
    storm_app = models.ForeignKey(StormApp)
    active = models.BooleanField(default=False, verbose_name='激活')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, verbose_name='创建人')
    md5 = models.CharField(max_length=64, blank=True, default='')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Storm应用Jar包'
        verbose_name_plural = 'Storm应用Jar包列表'

    def __unicode__(self):
        return os.path.basename(self.url)

    def save(self, *args, **kwargs):
        if self.package:
            if os.path.isfile(self.package.path):
                self.md5 = hashlib.md5(open(self.package.path, 'rb').read()).hexdigest()
        return super(StormAppJar, self).save(*args, **kwargs)

    @property
    def is_ready(self):
        return self.state == 2

    @property
    def url_filename(self):
        return os.path.basename(self.url)

    def get_download_url(self):
        return urlparse.urljoin(settings.MAIN_URL, self.package.url)

    def get_active_url(self):
        return reverse('active_jar', args=[self.id])

    def get_update_url(self):
        return reverse('storm_app_jar_update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('storm_app_jar_delete', kwargs={'pk': self.pk})
    
    
class StormNodeJarDir(models.Model):
    jar_dir = models.CharField(max_length=64, verbose_name='jar包目录')
    note = models.TextField(blank=True, default='', verbose_name='描述')
    storm_node = models.ForeignKey(StormNode)

    class Meta:
        verbose_name = 'Jar包目录'
        verbose_name_plural = 'Jar包目录列表'

    def __unicode__(self):
        return self.jar_dir

    def get_update_url(self):
        return reverse('storm_node_jar_dir_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('storm_node_jar_dir_delete', kwargs={'pk': self.id})


class StormAppNode(models.Model):
    app = models.ForeignKey(StormApp, on_delete=models.CASCADE)
    node = models.ForeignKey(StormNode, on_delete=models.CASCADE)
    jar_dir = models.ForeignKey(StormNodeJarDir, blank=True, null=True, on_delete=models.SET_NULL)
