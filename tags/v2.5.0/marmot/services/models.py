# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import re
import time
import urlparse
import uuid
import hashlib
import logging
import xmlrpclib
import httplib
import collections
import redis

from django.db import models
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings

from utils import icegridadmin, file_md5
from utils.node_proxy import NodeProxy
from assets.models import Server


RDS = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)

errlog = logging.getLogger('marmot')


class IceServiceCenter(models.Model):
    name = models.CharField(max_length=48, unique=True, verbose_name='名称')
    prefix = models.CharField(max_length=48, verbose_name='注册中心标识')
    master_server = models.ForeignKey(
        Server, on_delete=models.PROTECT, verbose_name='注册中心(master)', related_name='master_server_set'
    )
    master_port = models.PositiveIntegerField(verbose_name='端口(master)')
    slave_server = models.ForeignKey(
        Server, on_delete=models.SET_NULL, verbose_name='注册中心(slave)', related_name='slave_server_set',
        blank=True, null=True
    )
    slave_port = models.PositiveIntegerField(verbose_name='端口(slave)', blank=True, null=True)
    admin_user = models.CharField(max_length=32, verbose_name='admin用户名')
    admin_password = models.CharField(max_length=32, verbose_name='admin密码')
    note = models.TextField(blank=True, default='', verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ICE注册中心'
        verbose_name_plural = 'ICE注册中心列表'
        permissions = (
            ("deploy_service", "Can deploy service"),
        )

    def get_admin(self):
        admin = icegridadmin.IceGridAdmin(
            self.admin_user, self.admin_password, settings.ICEGRIDADMIN,
            master_ip=self.master_server.ip, master_port=self.master_port,
            slave_ip=self.slave_server.ip if self.slave_server else None, slave_port=self.slave_port,
            prefix=self.prefix
        )
        return admin

    def get_all_registry_info(self):
        admin = self.get_admin()
        try:
            admin.initialize()
        except icegridadmin.InitializeException:
            return
        else:
            return [admin.get_registry_info(i) for i in admin.get_all_registry_names()]
        finally:
            admin.destroy()

    def get_ice_nodes(self):
        nodes = []
        for node in self.get_all_node_info():
            nodes.append(IceNode(node['name'], node['info']['hostname']))
        return nodes

    def get_ice_node(self, name):
        admin = self.get_admin()
        try:
            admin.initialize()
        except icegridadmin.InitializeException:
            return
        else:
            info = admin.get_node_info(name)
            return IceNode(name, info.hostname)
        finally:
            admin.destroy()

    def get_all_node_names(self):
        admin = self.get_admin()
        try:
            admin.initialize()
        except icegridadmin.InitializeException:
            return
        else:
            return admin.get_all_node_names()
        finally:
            admin.destroy()

    def get_all_node_info(self):
        admin = self.get_admin()
        try:
            admin.initialize()
        except icegridadmin.InitializeException:
            return []
        else:
            all_node_info = []
            for node in admin.get_all_node_names():
                try:
                    info = vars(admin.get_node_info(node))
                    load = vars(admin.get_node_load(node))
                except TypeError:
                    continue
                all_node_info.append({
                    'name': info.pop('name'),
                    'info': info,
                    'load': collections.OrderedDict(sorted(load.items(), key=lambda d: int(d[0][3:]))),
                })
            return all_node_info
        finally:
            admin.destroy()

    def get_all_app_info(self):
        admin = self.get_admin()
        try:
            admin.initialize()
        except icegridadmin.InitializeException:
            return
        else:
            return {name: admin.get_application_servers(name) for name in admin.get_all_application_names()}
        finally:
            admin.destroy()

    def get_absolute_url(self):
        return '/services/ice-service-center/%s' % self.id

    def get_update_url(self):
        return '/services/ice-service-center/update/%s/' % self.id

    def get_delete_url(self):
        return '/services/ice-service-center/delete/%s/' % self.id

    def __unicode__(self):
        return self.name


class IceNode(object):
    def __init__(self, name, hostname):
        self.name = name
        self.hostname = hostname
        self.host = self._get_host()
        self.package_dir = '/opt/ice_project/'

    def _get_host(self):
        try:
            return Server.objects.get(hostname=self.hostname)
        except Server.DoesNotExist:
            return

    def push_task(self, task):
        node = NodeProxy(self.host.ip, settings.NODE_PORT)
        task['pkg_dest_dir'] = os.path.join(self.package_dir, 'lib64', task.pop('dir_name'))
        task['node_name'] = self.name
        node.add_task(task)

    def is_online(self):
        return self.host.is_alive

    def __unicode__(self):
        return '%s - %s' % (self.hostname, self.host.ip)


class IceServiceJar(models.Model):
    STATE_CHOICES = (
        (1, '下载中'),
        (2, '下载完成'),
        (3, '下载失败'),
    )
    url = models.URLField(verbose_name='程序包地址')
    package = models.FileField(upload_to='ice_services/jar/', blank=True, null=True)
    state = models.IntegerField(verbose_name='状态', choices=STATE_CHOICES, default=1)
    active = models.BooleanField(default=False, verbose_name='激活')
    ice_service = models.ForeignKey('IceService')

    note = models.TextField(blank=True, default='', verbose_name='描述')
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='创建人')
    md5 = models.CharField(max_length=64, blank=True, default='')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'ICE服务Jar包地址'
        verbose_name_plural = 'ICE服务Jar包地址列表'
        # unique_together = (('ice_service', 'url'),)

    def save(self, *args, **kwargs):
        if os.path.isfile(self.package.path):
            self.md5 = hashlib.md5(open(self.package.path, 'rb').read()).hexdigest()
        return super(IceServiceJar, self).save(*args, **kwargs)

    @property
    def finished(self):
        return self.state == 2

    def get_active_url(self):
        return reverse('active_jar', args=[self.id])

    def get_update_url(self):
        return reverse('ice_service_jar_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('delete_jar', args=[self.id])

    def __unicode__(self):
        return os.path.basename(self.url)


@receiver(models.signals.post_delete, sender=IceServiceJar)
def auto_delete_jar_on_delete(sender, instance, **kwargs):
    """
    Deletes jar-package from filesystem
    when corresponding 'IceServiceJar' object is deleted.
    """
    if instance.package:
        if os.path.isfile(instance.package.path):
            os.remove(instance.package.path)


@receiver(models.signals.pre_save, sender=IceServiceJar)
def auto_delete_jar_on_change(sender, instance, **kwargs):
    """
    Deletes jar-package from filesystem
    when corresponding 'IceServiceJar' object is changed.
    """
    if instance.pk is None:
        return False
    try:
        old_jar = IceServiceJar.objects.get(pk=instance.pk)
    except IceServiceJar.DoesNotExist:
        return False

    if old_jar.package and (old_jar.url != instance.url):
        if os.path.isfile(old_jar.package.path):
            os.remove(old_jar.package.path)


def process_filename(instance, filename):
    """filename.zip -> filename(uuid).zip"""
    fn, ext = os.path.splitext(filename)
    return 'ice_services/config/{0}({1}){2}'.format(fn, uuid.uuid4().get_hex(), ext)


class IceServiceConfig(models.Model):
    config = models.FileField(upload_to=process_filename, verbose_name='配置文件(zip)')
    active = models.BooleanField(default=False)
    ice_service = models.ForeignKey('IceService')

    note = models.TextField(blank=True, default='', verbose_name='描述')
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='创建人')
    md5 = models.CharField(max_length=64, blank=True, default='')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'ICE服务配置文件'
        verbose_name_plural = 'ICE服务配置文件列表'

    def save(self, *args, **kwargs):
        if os.path.isfile(self.config.path):
            self.md5 = hashlib.md5(open(self.config.path, 'rb').read()).hexdigest()
        return super(IceServiceConfig, self).save(*args, **kwargs)

    def get_active_url(self):
        return reverse('active_config', args=[self.id])

    def get_update_url(self):
        return reverse('ice_service_config_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('delete_config', args=[self.id])

    def config_real_name(self):
        basename = os.path.basename(self.config.name)
        ret = re.findall(r'\(\S+?\)', basename)
        if ret:
            return basename.replace(ret[-1], '')
        else:
            return basename

    def get_uuid_str(self):
        basename = os.path.basename(self.config.name)
        ret = re.findall(r'(?<=\()\S+?(?=\))', basename)
        return ret[-1] if ret else ''

    def __unicode__(self):
        return self.config.name


@receiver(models.signals.post_delete, sender=IceServiceConfig)
def auto_delete_config_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding 'IceServiceConfig' object is deleted.
    """
    if instance.config:
        if os.path.isfile(instance.config.path):
            os.remove(instance.config.path)


@receiver(models.signals.pre_save, sender=IceServiceConfig)
def auto_delete_config_file_on_change(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding 'IceServiceConfig' object is changed.
    """
    if instance.pk is None:
        return False
    try:
        old_file = IceServiceConfig.objects.get(pk=instance.pk).config
    except IceServiceConfig.DoesNotExist:
        return False

    new_file = instance.config
    if old_file != new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)


class IceService(models.Model):
    center = models.ForeignKey(IceServiceCenter, on_delete=models.CASCADE, verbose_name='注册中心')
    name = models.CharField(max_length=64, verbose_name='App名称')
    dir_name = models.CharField(max_length=64, verbose_name='工程目录名称')
    xml = models.FileField(upload_to='ice_services', verbose_name='部署文件(xml)')
    version = models.CharField(max_length=32, verbose_name='版本')
    users = models.ManyToManyField(User, blank=True, verbose_name='开发者')
    deployed = models.BooleanField(default=False, verbose_name='已部署')
    note = models.TextField(blank=True, default='', verbose_name='描述')

    identifier = models.UUIDField(default=uuid.uuid4, editable=False, verbose_name='标识')
    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ICE服务'
        verbose_name_plural = 'ICE服务列表'
        # unique_together = (('center', 'name'), ('center', 'dir_name'))

    def __unicode__(self):
        return self.name + ' - ' + self.center.name

    @classmethod
    def type(cls):
        return 'ice'

    @property
    def hex_identifier(self):
        return self.identifier.get_hex()

    def get_users_display(self):
        return '; '.join([user.get_full_name() for user in self.users.all()])

    def get_active_jar(self):
        return self.iceservicejar_set.filter(active=True).first()

    def get_active_config(self):
        return self.iceserviceconfig_set.filter(active=True).first()

    def to_task(self):
        jar = self.get_active_jar()
        conf = self.get_active_config()
        return {
            'type': 'ice',
            'identifier': self.hex_identifier,
            'name': self.name,
            'dir_name': self.dir_name,
            'jar': urlparse.urljoin(settings.MAIN_URL,  jar.package.url) if jar else '',
            'jar_md5': jar.md5,
            'conf': urlparse.urljoin(settings.MAIN_URL, conf.config.url) if conf else '',
            'conf_md5': conf.md5,
        }

    def push_task_to_all_node(self, priority=1):
        task = self.to_task()
        task['priority'] = priority
        nodes = self.center.get_ice_nodes()
        for node in nodes:
            node.push_task(task.copy())

    def push_task_to_node(self, node_name, priority=1):
        task = self.to_task()
        task['priority'] = priority
        node = self.center.get_ice_node(node_name)
        node.push_task(task)

    def deploy(self):
        admin = self.center.get_admin()
        try:
            admin.initialize()
        except icegridadmin.InitializeException:
            return
        else:
            descriptor_new = admin.xml_to_app_descriptor(self.xml.path)
            if admin.application_exist(self.name):
                descriptor_old = admin.get_application_descriptor(self.name)
                if descriptor_new != descriptor_old:
                    admin.sync_application(descriptor_new)
                # 此处待优化: ice文档中描述 sync_application 方法会重启ice服务,
                # 但实际测试并没有重启, 而是关闭.
                # 所以下面用for遍历了server的各个节点来重启
                servers = []
                for node in descriptor_new.nodes.values():
                    servers.append(node.serverInstances[0].parameterValues['id'])
                for server in servers:
                    try:
                        admin.stop_server(server)
                    except Exception:
                        errlog.exception('ice server stop error - server-node: %s' % server)
                    try:
                        admin.start_server(server)
                    except Exception:
                        errlog.exception('ice node start error - node: %s' % server)
            else:
                admin.add_application(descriptor_new)
                servers = admin.get_application_servers_from_descriptor(descriptor_new)
                for server in servers:
                    try:
                        admin.start_server(server)
                    except Exception:
                        errlog.exception('ice node start error - node: %s' % server)
                return True
        finally:
            admin.destroy()

    def sync_application_without_restart(self):
        admin = self.center.get_admin()
        try:
            admin.initialize()
        except icegridadmin.InitializeException:
            return
        else:
            descriptor = admin.xml_to_app_descriptor(self.xml.path)
            return admin.sync_application_without_restart(descriptor)
        finally:
            admin.destroy()

    def remove_service(self):
        admin = self.center.get_admin()
        try:
            admin.initialize()
        except icegridadmin.InitializeException:
            return
        else:
            return admin.remove_application(self.name)
        finally:
            admin.destroy()

    def start_server(self, server_id):
        admin = self.center.get_admin()
        try:
            admin.initialize()
        except icegridadmin.InitializeException:
            return
        else:
            return admin.start_server(server_id)
        finally:
            admin.destroy()

    def stop_server(self, server_id):
        admin = self.center.get_admin()
        try:
            admin.initialize()
        except icegridadmin.InitializeException:
            return
        else:
            return admin.stop_server(server_id)
        finally:
            admin.destroy()

    def restart_server(self, server_id):
        admin = self.center.get_admin()
        try:
            admin.initialize()
        except icegridadmin.InitializeException:
            return
        else:
            admin.stop_server(server_id)
            admin.start_server(server_id)
        finally:
            admin.destroy()

    def get_application_servers(self):
        admin = self.center.get_admin()
        try:
            admin.initialize()
        except icegridadmin.InitializeException:
            return
        else:
            return admin.get_application_servers(self.name)
        finally:
            admin.destroy()

    def get_absolute_url(self):
        return reverse('ice_service_detail', kwargs={'pk': self.pk})

    def get_update_url(self):
        return reverse('ice_service_update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('ice_service_delete', kwargs={'pk': self.pk})


@receiver(models.signals.post_delete, sender=IceService)
def auto_delete_xml_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding 'IceService' object is deleted.
    """
    if instance.xml:
        if os.path.isfile(instance.xml.path):
            os.remove(instance.xml.path)


@receiver(models.signals.pre_save, sender=IceService)
def auto_delete_xml_on_change(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding 'IceService' object is changed.
    """
    if instance.pk is None:
        return False
    try:
        old_file = IceService.objects.get(pk=instance.pk).xml
    except IceService.DoesNotExist:
        return False

    new_file = instance.xml
    if old_file != new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)


class TomcatGroup(models.Model):
    name = models.CharField(max_length=48, verbose_name='名称')
    note = models.TextField(verbose_name='描述', blank=True, default='')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'TomcatGroup'
        verbose_name_plural = 'TomcatGroups'

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('tomcat_group_detail', args=[self.pk])

    def get_update_url(self):
        return reverse('tomcat_group_update', args=[self.pk])

    def get_delete_url(self):
        return reverse('tomcat_group_delete', args=[self.pk])


class TomcatCluster(models.Model):
    group = models.ForeignKey(TomcatGroup)
    name = models.CharField(max_length=48, verbose_name='名称')
    note = models.TextField(blank=True, default='', verbose_name='描述')
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tomcat集群'
        verbose_name_plural = 'Tomcat集群列表'
        permissions = {
            ('operate_tomcat', "start stop tomcat-server"),
            ('operate_db', "backup db"),
            ('execute_sql', "execute sql"),
            ('push_war_pkg', "push war package"),
        }

    def __unicode__(self):
        return '%s - %s' % (self.name, self.group.name)

    def get_absolute_url(self):
        return reverse('tomcat_cluster_detail', args=[self.pk])

    def get_update_url(self):
        return reverse('tomcat_cluster_update', args=[self.pk])

    def get_delete_url(self):
        return reverse('tomcat_cluster_delete', args=[self.pk])


class TomcatServer(models.Model):
    cluster = models.ForeignKey(TomcatCluster)
    name = models.CharField(max_length=48, verbose_name='名称')
    host = models.ForeignKey(Server, verbose_name='主机')
    port = models.PositiveIntegerField(verbose_name='端口')
    cmd = models.CharField(max_length=64, verbose_name='tomcat启动命令')
    note = models.TextField(blank=True, default='', verbose_name='描述')

    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='创建人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tomcat服务器'
        verbose_name_plural = 'Tomcat服务器列表'
        unique_together = (('host', 'cmd'),)

    def __unicode__(self):
        return '%s - %s' % (self.name, self.host)

    def kill(self):
        node = NodeProxy(self.host.ip, settings.NODE_PORT)
        try:
            return node.kill_process(self.cmd)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return False

    def start(self):
        node = NodeProxy(self.host.ip, settings.NODE_PORT)
        try:
            return node.start_tomcat(self.cmd)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return False

    def is_alive(self):
        node = NodeProxy(self.host.ip, settings.NODE_PORT)
        try:
            return node.tomcat_is_alive(self.cmd)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return False

    def restart(self):
        node = NodeProxy(self.host.ip, settings.NODE_PORT)
        node.kill_process(self.cmd)
        time.sleep(0.1)  # TODO 这个延时是否有必要, 待测试
        node.start_tomcat(self.cmd)

    def get_absolute_url(self):
        return reverse('tomcat_server_detail', args=[self.pk])

    def get_update_url(self):
        return reverse('tomcat_server_update', args=[self.pk])

    def get_delete_url(self):
        return reverse('tomcat_server_delete', args=[self.pk])


class TomcatServerWarDir(models.Model):
    war_dir = models.CharField(max_length=64, verbose_name='war包目录')
    note = models.TextField(blank=True, default='', verbose_name='描述')
    tomcat_server = models.ForeignKey(TomcatServer)

    class Meta:
        verbose_name = 'war包目录'
        verbose_name_plural = 'war包目录列表'

    def __unicode__(self):
        return self.war_dir

    def get_update_url(self):
        return reverse('tomcat_server_war_dir_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('tomcat_server_war_dir_delete', kwargs={'pk': self.id})


class TomcatApp(models.Model):
    cluster = models.ForeignKey(TomcatCluster)
    name = models.CharField(max_length=48, verbose_name='名称')
    note = models.TextField(blank=True, default='', verbose_name='描述')

    users = models.ManyToManyField(User, blank=True, verbose_name='开发者')
    identifier = models.UUIDField(default=uuid.uuid4, editable=False, verbose_name='标识')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tomcat应用'
        verbose_name_plural = 'Tomcat应用列表'
        unique_together = (('cluster', 'name'),)

    def __unicode__(self):
        return '{0} - {1}({2})'.format(self.name, self.cluster.name, self.cluster.group.name)

    @classmethod
    def type(cls):
        return 'tomcat'

    @property
    def hex_identifier(self):
        return self.identifier.get_hex()

    def get_users_display(self):
        return '; '.join([user.get_full_name() for user in self.users.all()])

    def get_active_war(self):
        return self.tomcatappwar_set.filter(active=True).first()

    def get_active_sql(self):
        return self.tomcatappsql_set.filter(active=True).first()

    def push_war(self, war, tomcat_app_node, priority=1):
        task = {
            'type': 'tomcat',
            'host': tomcat_app_node.server.host.ip,
            'app_name': self.name,
            'identifier': self.hex_identifier,
            'priority': priority,
            'war_dir': tomcat_app_node.war_dir.war_dir,
            'war_url': war.get_download_url(),
            'war_md5': war.md5,
        }
        node = NodeProxy(tomcat_app_node.server.host.ip, settings.NODE_PORT)
        return node.add_task(task)

    def get_absolute_url(self):
        return reverse('tomcat_app_detail', args=[self.pk])

    def get_update_url(self):
        return reverse('tomcat_app_update', args=[self.pk])

    def get_delete_url(self):
        return reverse('tomcat_app_delete', args=[self.pk])


class TomcatAppNode(models.Model):
    app = models.ForeignKey(TomcatApp, on_delete=models.CASCADE)
    server = models.ForeignKey(TomcatServer, on_delete=models.CASCADE)
    war_dir = models.ForeignKey(TomcatServerWarDir, blank=True, null=True, on_delete=models.SET_NULL)


class TomcatAppDB(models.Model):
    STATE_CHOICES = (
        (1, '空闲'),
        (2, '正在备份'),
        (3, '正在执行SQL'),
    )
    app = models.ForeignKey(TomcatApp, on_delete=models.CASCADE)
    name = models.CharField(max_length=48, verbose_name='数据库名')
    ip = models.GenericIPAddressField(verbose_name='地址')
    port = models.PositiveIntegerField(verbose_name='端口')
    user = models.CharField(max_length=48, verbose_name='账号')
    pwd = models.CharField(max_length=48, verbose_name='密码')
    state = models.PositiveIntegerField(verbose_name='状态', choices=STATE_CHOICES, default=1)
    note = models.TextField(verbose_name='描述', blank=True, default='')

    class Meta:
        verbose_name = 'TomcatApp数据库'
        verbose_name_plural = 'TomcatApp数据库列表'

    def __unicode__(self):
        return self.name + ' - ' + self.ip

    @property
    def is_ready(self):
        return self.state == 1

    def get_absolute_url(self):
        return reverse('tomcat_app_db_detail', kwargs={'pk': self.pk})

    def get_update_url(self):
        return reverse('tomcat_app_db_update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('tomcat_app_db_delete', kwargs={'pk': self.pk})


class TomcatAppWar(models.Model):
    STATE_CHOICES = (
        (1, '下载中'),
        (2, '就绪'),
        (3, '下载失败'),
    )
    url = models.URLField(verbose_name='war包地址')
    package = models.FileField(upload_to='tomcat_apps/war/', blank=True, null=True)
    state = models.IntegerField(verbose_name='状态', choices=STATE_CHOICES, default=1)
    note = models.TextField(verbose_name='描述', blank=True, default='')
    tomcat_app = models.ForeignKey(TomcatApp)
    active = models.BooleanField(default=False, verbose_name='激活')

    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='创建人')
    md5 = models.CharField(max_length=64, blank=True, default='')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tomcat应用War包'
        verbose_name_plural = 'Tomcat应用War包列表'

    def __unicode__(self):
        return os.path.basename(self.url)

    def save(self, *args, **kwargs):
        if self.package:
            if os.path.isfile(self.package.path):
                self.md5 = hashlib.md5(open(self.package.path, 'rb').read()).hexdigest()
        return super(TomcatAppWar, self).save(*args, **kwargs)

    @property
    def is_ready(self):
        return self.state == 2

    @property
    def url_filename(self):
        return os.path.basename(self.url)

    def get_download_url(self):
        return urlparse.urljoin(settings.MAIN_URL, self.package.url)

    def get_active_url(self):
        return reverse('active_war', args=[self.id])

    def get_update_url(self):
        return reverse('tomcat_app_war_update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('tomcat_app_war_delete', kwargs={'pk': self.pk})


@receiver(models.signals.post_delete, sender=TomcatAppWar)
def auto_delete_war_on_delete(sender, instance, **kwargs):
    """
    Deletes war-package from filesystem
    when corresponding 'TomcatAppWar' object is deleted.
    """
    if instance.package:
        if os.path.isfile(instance.package.path):
            os.remove(instance.package.path)


@receiver(models.signals.pre_save, sender=TomcatAppWar)
def auto_delete_war_on_change(sender, instance, **kwargs):
    """
    Deletes war-package from filesystem
    when corresponding 'TomcatAppWar' object is changed.
    """
    if instance.pk is None:
        return False
    try:
        old_war = TomcatAppWar.objects.get(pk=instance.pk)
    except TomcatAppWar.DoesNotExist:
        return False

    if old_war.package and (old_war.url != instance.url):
        if os.path.isfile(old_war.package.path):
            os.remove(old_war.package.path)


class TomcatAppSql(models.Model):
    STATE_CHOICES = (
        (1, '空闲'),
        (2, '执行'),
    )
    sql = models.FileField(verbose_name='sql文件', upload_to='tomcat_apps/sql/')
    state = models.IntegerField(verbose_name='状态', choices=STATE_CHOICES, default=1)
    note = models.TextField(verbose_name='描述', blank=True, default='')
    sys_bak = models.BooleanField(verbose_name='系统备份flag', default=False)
    db = models.ForeignKey(TomcatAppDB, verbose_name='数据库')
    tomcat_app = models.ForeignKey(TomcatApp)

    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tomcat应用SQL文件'
        verbose_name_plural = 'Tomcat应用SQL文件列表'

    def __unicode__(self):
        return os.path.basename(self.sql.name)

    @property
    def is_ready(self):
        return self.state != 2

    @property
    def sql_filename(self):
        return os.path.basename(self.sql.name)

    def get_update_url(self):
        return reverse('tomcat_app_sql_update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('tomcat_app_sql_delete', kwargs={'pk': self.pk})


@receiver(models.signals.post_delete, sender=TomcatAppSql)
def auto_delete_sql_on_delete(sender, instance, **kwargs):
    """
    Deletes sql-file from filesystem
    when corresponding 'TomcatAppSql' object is deleted.
    """
    if instance.sql:
        if os.path.isfile(instance.sql.path):
            os.remove(instance.sql.path)


@receiver(models.signals.pre_save, sender=TomcatAppSql)
def auto_delete_sql_on_change(sender, instance, **kwargs):
    """
    Deletes sql-file from filesystem
    when corresponding 'TomcatAppSql' object is changed.
    """
    if instance.pk is None:
        return False
    try:
        old_file = TomcatAppSql.objects.get(pk=instance.pk).sql
    except TomcatAppSql.DoesNotExist:
        return False

    new_file = instance.sql
    if old_file != new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)
