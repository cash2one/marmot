# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import urllib
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
from .fields import FileFieldOnly

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
        return self.name

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
        return self.name

    @property
    def script_short_name(self):
        return os.path.basename(self.script.name)

    def is_alive(self, node):
        try:
            resp = urllib.urlopen("http://{0}:{1}/ping".format(node.server.ip, self.port))
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


class SpringCloudFile(models.Model):
    TYPE_CHOICES = (
        (0, 'lib'),
        (1, 'lib/libs'),
        (2, 'config')
    )

    file = FileFieldOnly(verbose_name='文件')
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
        return human_size(self.file.size)

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


class SpringCloudFileDeleteError(Exception):
    pass


class SpringCloudFileDeleteSuccess(Exception):
    pass


@receiver(models.signals.post_delete, sender=SpringCloudFile)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)

    if instance.type == 0:
        rel_path = os.path.join('lib', unicode(instance))
    elif instance.type == 1:
        rel_path = os.path.join('lib', 'libs', unicode(instance))
    elif instance.type == 2:
        rel_path = os.path.join('config', unicode(instance))
    else:
        raise SpringCloudFileDeleteError('SpringCloudFile - type: %s ERROR!' % instance.type)

    # 删除节点上的文件
    error_list = []
    for node in instance.app.nodes.all():
        proxy = NodeProxy(node.server.ip, settings.NODE_PORT, timeout=5.0)
        try:
            stat, msg = proxy.remove(os.path.join(node.cwd, 'app', instance.app.name, rel_path))
            if not stat:
                error_list.append('%s - %s' % (node.server, unicode(msg, 'utf-8')))
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine) as e:
            error_list.append('%s - %s' % (node.server, str(e)))

    if error_list:
        raise SpringCloudFileDeleteError('\n'.join(error_list))

    # TODO 这里用异常去提示成功的方式, 不合理, 待优化
    raise SpringCloudFileDeleteSuccess('Success')
