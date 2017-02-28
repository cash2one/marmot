# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import urlparse
import httplib
import xmlrpclib

from django.db import models
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings

from utils.node_proxy import NodeProxy

from assets.models import Server


class NodeApp(models.Model):

    name = models.CharField('名称', max_length=128)
    server = models.ForeignKey(Server, verbose_name='服务器', on_delete=models.PROTECT)
    cwd = models.CharField('工程目录', max_length=255)
    main = models.CharField('主脚本', max_length=255)
    note = models.TextField('备注', blank=True, default='')

    pid = models.CharField('pid', blank=True, default='', max_length=8)
    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Node应用'
        verbose_name_plural = 'Node应用列表'
        ordering = ['-id']
        unique_together = (('name', 'server'),)
        permissions = (
            ('operate_nodeapp', 'Can startup/kill node-app'),
        )

    def __unicode__(self):
        return self.name

    def startup(self):
        node = NodeProxy(self.server.ip, settings.NODE_PORT)
        try:
            pid, stdout = node.startup_node_app(self.name, self.main, self.cwd)
            if pid != -1:
                # 启动成功
                self.pid = str(pid)
                self.save()
            return stdout
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine) as e:
            return str(e)

    def kill(self):
        if not self.pid:
            return False
        node = NodeProxy(self.server.ip, settings.NODE_PORT)
        try:
            return node.kill_pid(self.pid)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return False

    def is_alive(self):
        if not self.pid:
            return False
        node = NodeProxy(self.server.ip, settings.NODE_PORT)
        try:
            return node.pid_is_alive(self.pid)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return False

    def get_absolute_url(self):
        return reverse('node_app_detail', kwargs={'pk': self.pk})

    def get_update_url(self):
        return reverse('node_app_update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('node_app_delete', kwargs={'pk': self.pk})


class NodeSrcPkg(models.Model):

    package = models.FileField(upload_to='nodejs/', verbose_name='源码包(zip)')
    note = models.TextField('备注', blank=True, default='')
    app = models.ForeignKey(NodeApp, verbose_name='node应用')

    active = models.BooleanField('线上', default=False)
    md5 = models.CharField(max_length=64, blank=True, default='')
    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Node源码包'
        verbose_name_plural = 'Node源码包列表'
        ordering = ['-id']
        permissions = (
            ('push_nodesrcpkg', 'Can push node source package'),
        )

    def __unicode__(self):
        return os.path.basename(self.package.name)

    def push_to_server(self, ident):
        node = NodeProxy(self.app.server.ip, settings.NODE_PORT)
        try:
            return node.task_node_src_pkg(self.app.name, self.get_download_url(),
                                              self.app.cwd, ident, self.md5)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return False

    def get_download_url(self):
        return urlparse.urljoin(settings.MAIN_URL, self.package.url)

    def get_absolute_url(self):
        return reverse('node_src_pkg_detail', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('node_src_pkg_delete', kwargs={'pk': self.pk})


@receiver(models.signals.post_delete, sender=NodeSrcPkg)
def auto_delete_pkg_file_on_delete(sender, instance, **kwargs):
    if instance.package:
        if os.path.isfile(instance.package.path):
            os.remove(instance.package.path)


@receiver(models.signals.pre_save, sender=NodeSrcPkg)
def auto_delete_pkg_file_on_change(sender, instance, **kwargs):
    if instance.pk is None:
        return False

    try:
        old_file = NodeSrcPkg.objects.get(pk=instance.pk).package
    except NodeSrcPkg.DoesNotExist:
        return False

    new_file = instance.package
    if old_file != new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)
