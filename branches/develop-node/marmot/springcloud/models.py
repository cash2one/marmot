# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import urllib
import urllib2
import hashlib
import urlparse
import httplib
import xmlrpclib
import logging

from django.db import models
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings

from utils import human_size
from utils.node_proxy import NodeProxy
from assets.models import Server
from monitor.fields import PortField

from .storages import OverwriteStorage

logger = logging.getLogger('marmot')


class SpringCloudCluster(models.Model):

    name = models.CharField('名称', max_length=128)
    note = models.TextField('备注', blank=True, default='')

    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'SpringCloud集群'
        verbose_name_plural = 'SpringCloud集群列表'
        ordering = ['-id']
        permissions = (
            ('operate_springcloudapp', 'Can startup/kill/sync-file'),
            ('delete_springcloudapp_files', 'Can delete springcloud-files'),
        )

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('springcloud_cluster_detail', kwargs={'pk': self.pk})

    def get_update_url(self):
        return reverse('springcloud_cluster_update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('springcloud_cluster_delete', kwargs={'pk': self.pk})


class SpringCloudNode(models.Model):

    name = models.CharField('名称', max_length=128)
    server = models.ForeignKey(Server, verbose_name='服务器', on_delete=models.PROTECT)
    cluster = models.ForeignKey(SpringCloudCluster, verbose_name='集群')
    cwd = models.CharField('工程目录', max_length=255)
    note = models.TextField('备注', blank=True, default='')

    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'SpringCloud节点'
        verbose_name_plural = 'SpringCloud节点列表'
        ordering = ['-id']
        unique_together = (
            ('name', 'cluster'),
            ('server', 'cluster'),
        )

    def __unicode__(self):
        return '%s - %s' % (self.name, self.server.hostname)

    def is_online(self):
        return self.server.is_alive

    def get_absolute_url(self):
        return reverse('springcloud_node_detail', kwargs={'pk': self.pk})

    def get_update_url(self):
        return reverse('springcloud_node_update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('springcloud_node_delete', kwargs={'pk': self.pk})


def process_filename(instance, filename):
    """处理微服务启动脚本的文件名"""
    return 'springcloud/{0}/{1}/bin/{2}'.format(instance.cluster.name, instance.name, filename)


class SpringCloudApp(models.Model):

    name = models.CharField('名称', max_length=128)
    startup = models.CharField('启动脚本', max_length=255)
    script = models.FileField(upload_to=process_filename, verbose_name='启动脚本文件',
                              blank=True, storage=OverwriteStorage())
    port = PortField('端口')

    cluster = models.ForeignKey(SpringCloudCluster, verbose_name='集群')
    nodes = models.ManyToManyField(SpringCloudNode, verbose_name='节点')
    develops = models.ManyToManyField(User, limit_choices_to={'profile__role__alias': 'developer'},
                                      verbose_name='开发者', related_name='springcloud_devs')

    note = models.TextField('备注', blank=True, default='')
    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'SpringCloud应用'
        verbose_name_plural = 'SpringCloud应用列表'
        ordering = ['-id']
        unique_together = (
            ('name', 'cluster'),
            ('startup', 'cluster'),
        )

    def __unicode__(self):
        return self.name + ' - ' + self.cluster.name

    @property
    def script_short_name(self):
        return os.path.basename(self.script.name)

    def is_alive(self, node):
        try:
            resp = urllib2.urlopen("http://{0}:{1}/ping".format(node.server.ip, self.port), timeout=3.0)
            res = resp.read()
            resp.close()
        except Exception:
            logger.exception('SpringCloud is alive Error')
            return False
        return 'pong' in res

    def start(self, node):
        proxy = NodeProxy(node.server.ip, settings.NODE_PORT, timeout=50.0)
        try:
            return proxy.springcloud_start(self.startup)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine) as e:
            return str(e)

    def kill(self, node):
        proxy = NodeProxy(node.server.ip, settings.NODE_PORT, timeout=50.0)
        try:
            return proxy.springcloud_stop(self.startup)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine) as e:
            return str(e)

    def sync_files(self, node, ident):
        proxy = NodeProxy(node.server.ip, settings.NODE_PORT)

        files = self.springcloudfile_set.all()

        task_files = []
        # task列表的第一个为同步启动脚本的task
        if self.script:
            task_files.append({'url': urlparse.urljoin(settings.MAIN_URL, self.script.url),
                               'md5': hashlib.md5(open(self.script.path, 'rb').read()).hexdigest(),
                               'rel_path': os.path.join(node.cwd, 'bin', self.script_short_name)})
        else:
            task_files.append('')

        for f in files:
            task_files.append(f.to_task())

        if not task_files:
            return False, '工程没有文件, 你同步个啥!'

        try:
            clear = False  # 是否清除原工程目录中多余的文件
            return proxy.springcloud_sync_files(self.name, node.cwd, task_files, ident, clear)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine) as e:
            return False, str(e)

    def get_absolute_url(self):
        return reverse('springcloud_app_detail', kwargs={'pk': self.pk})

    def get_update_url(self):
        return reverse('springcloud_app_update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('springcloud_app_delete', kwargs={'pk': self.pk})


@receiver(models.signals.post_delete, sender=SpringCloudApp)
def auto_delete_script_on_delete(sender, instance, **kwargs):
    if instance.script:
        if os.path.isfile(instance.script.path):
            os.remove(instance.script.path)


@receiver(models.signals.pre_save, sender=SpringCloudApp)
def auto_delete_script_on_change(sender, instance, **kwargs):
    if instance.pk is None:
        return False

    try:
        old_script = SpringCloudApp.objects.get(pk=instance.pk).script
    except SpringCloudApp.DoesNotExist:
        return False

    new_script = instance.script
    if old_script:
        if old_script != new_script:
            if os.path.isfile(old_script.path):
                os.remove(old_script.path)


class SpringCloudBackup(models.Model):

    path = models.CharField(verbose_name='路径', max_length=255)
    app = models.ForeignKey(SpringCloudApp, verbose_name='应用')
    node = models.ForeignKey(SpringCloudNode, verbose_name='节点')

    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'SpringCloud备份'
        verbose_name_plural = 'SpringCloud备份列表'
        ordering = ['-id']

    def rollback(self, identifier):
        proxy = NodeProxy(self.node.server.ip, settings.NODE_PORT)
        try:
            return proxy.springcloud_rollback(self.app.name, identifier, self.path)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine) as e:
            return str(e)

    def delete_remote_file(self):
        proxy = NodeProxy(self.node.server.ip, settings.NODE_PORT)
        try:
            return proxy.remove(self.path)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine) as e:
            return str(e)


@receiver(models.signals.post_delete, sender=SpringCloudBackup)
def auto_delete_remote_backup_on_delete(sender, instance, **kwargs):
    try:
        stat, msg = instance.delete_remote_file()
        if not stat:
            logger.error('Delete Remote-SpringCloud-backup-file Error: %s' % msg)
    except Exception:
        logger.exception('Delete Remote-SpringCloud-backup-file Error')


def process_scf_name(instance, filename):
    """处理微服务启动脚本的文件名"""
    app_name = instance.app.name
    cluster_name = instance.app.cluster.name
    _type = instance.type
    if _type == 0:
        return 'springcloud/{0}/{1}/lib/{2}'.format(cluster_name, app_name, filename)
    elif _type == 1:
        return 'springcloud/{0}/{1}/lib/libs/{2}'.format(cluster_name, app_name, filename)
    elif _type == 2:
        return 'springcloud/{0}/{1}/config/{2}'.format(cluster_name, app_name, filename)
    else:
        raise ValueError('SpringCloudFile - type: %s ERROR!' % _type)


class SpringCloudFile(models.Model):
    TYPE_CHOICES = (
        (0, 'lib'),
        (1, 'lib/libs'),
        (2, 'config')
    )

    file = models.FileField(upload_to=process_scf_name, max_length=200, verbose_name='文件', storage=OverwriteStorage())
    app = models.ForeignKey(SpringCloudApp, verbose_name='应用')
    type = models.IntegerField(choices=TYPE_CHOICES, default=0)

    md5 = models.CharField(max_length=64, blank=True, default='')

    created_by = models.ForeignKey(User, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'SpringCloudFile'
        verbose_name_plural = 'SpringCloudFile列表'
        ordering = ['-id']

    def __unicode__(self):
        return os.path.basename(self.file.name)

    @property
    def file_size(self):
        try:
            return human_size(self.file.size)
        except OSError:
            return 'File not found'

    def to_task(self):
        if self.type == 0:
            rel_path = os.path.join('lib', unicode(self))
        elif self.type == 1:
            rel_path = os.path.join('lib', 'libs', unicode(self))
        elif self.type == 2:
            rel_path = os.path.join('config', unicode(self))
        else:
            raise ValueError('SpringCloudFile - type: %s ERROR!' % self.type)
        return {
            'url': self.get_download_url(),
            'md5': self.md5,
            'rel_path': rel_path,
        }

    def get_download_url(self):
        return urlparse.urljoin(settings.MAIN_URL, self.file.url)

    def get_absolute_url(self):
        return reverse('springcloudfile_detail', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('springcloudfile_delete', kwargs={'pk': self.pk})


@receiver(models.signals.post_delete, sender=SpringCloudFile)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)
