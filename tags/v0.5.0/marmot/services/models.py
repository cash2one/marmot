# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import re
import uuid
import copy
import logging

from django.db import models
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings

from utils import connect_node
from utils.icegridadmin import IceGridAdmin
from assets.models import Server


errlog = logging.getLogger('marmot')


class IceServiceCenter(models.Model):
    name = models.CharField(max_length=48, unique=True, verbose_name='名称')
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
    note = models.TextField(blank=True, null=True, verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ICE服务注册中心'
        verbose_name_plural = 'ICE服务注册中心列表'

    def get_admin(self):
        admin = IceGridAdmin(
            self.admin_user, self.admin_password,
            master_ip=self.master_server.listen_ip, master_port=self.master_port,
            slave_ip=self.slave_server.listen_ip if self.slave_server else None, slave_port=self.slave_port
        )
        return admin

    def get_all_registry_info(self):
        admin = self.get_admin()
        try:
            admin.initialize()
        except RuntimeError:
            return
        else:
            return [admin.get_registry_info(i) for i in admin.get_all_registry_names()]
        finally:
            admin.destroy()

    def get_all_node_info(self):
        admin = self.get_admin()
        try:
            admin.initialize()
        except RuntimeError:
            return
        else:
            info = []
            for node in admin.get_all_node_names():
                node_info = admin.get_node_info(node)
                node_load = admin.get_node_load(node)
                info.append({'info': node_info, 'load': node_load})
            return info
        finally:
            admin.destroy()

    def get_all_app_info(self):
        admin = self.get_admin()
        try:
            admin.initialize()
        except RuntimeError:
            return
        else:
            return {name: admin.get_application_nodes(name) for name in admin.get_all_application_names()}
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


def process_filename(instance, filename):
    """filename.zip -> filename(uuid).zip"""
    filename, ext = os.path.splitext(filename)
    return 'ice_services/{0}({1}){2}'.format(filename, uuid.uuid4().get_hex(), ext)


class IceServiceNode(models.Model):
    center = models.ForeignKey(IceServiceCenter, on_delete=models.CASCADE, verbose_name='ICE注册中心')
    name = models.CharField(max_length=64, verbose_name='节点名称')
    host = models.ForeignKey(Server, on_delete=models.CASCADE, verbose_name='ICE节点')
    package_dir = models.CharField(max_length=255, verbose_name='程序包目录')
    user = models.ForeignKey(User, verbose_name='创建人')
    note = models.TextField(blank=True, null=True, verbose_name='描述')

    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ICE节点'
        verbose_name_plural = 'ICE节点列表'

    def push_task(self, task):
        node = connect_node(self.host.listen_ip)
        task['pkg_dest_dir'] = os.path.join(self.package_dir, 'lib64', task.pop('dir_name'))
        task['node_name'] = self.name
        node.add_task(task)

    def get_absolute_url(self):
        return '/services/ice-service-node/%s' % self.id

    def get_update_url(self):
        return '/services/ice-service-node/update/%s/' % self.id

    def get_delete_url(self):
        return '/services/ice-service-node/delete/%s/' % self.id

    def __unicode__(self):
        return self.name


class IceService(models.Model):
    center = models.ForeignKey(IceServiceCenter, on_delete=models.CASCADE, verbose_name='注册中心')
    name = models.CharField(max_length=64, verbose_name='App名称')
    dir_name = models.CharField(max_length=64, verbose_name='工程目录名称')
    package = models.FileField(upload_to=process_filename, verbose_name='程序包(zip)')
    xml = models.FileField(upload_to='ice_services', verbose_name='部署文件(xml)')
    version = models.CharField(max_length=32, verbose_name='版本')
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='创建人')
    deployed = models.BooleanField(default=False, verbose_name='已部署')
    note = models.TextField(blank=True, null=True, verbose_name='描述')

    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ICE服务'
        verbose_name_plural = 'ICE服务列表'
        # unique_together = (('center', 'name'), ('center', 'dir_name'))
        permissions = (
            ("deploy", "Can deploy service"),
        )

    def package_real_name(self):
        basename = os.path.basename(self.package.name)
        ret = re.findall(r'\(\S+?\)', basename)
        if ret:
            return basename.replace(ret[-1], '')
        else:
            return basename

    def get_uuid_str(self):
        basename = os.path.basename(self.package.name)
        ret = re.findall(r'(?<=\()\S+?(?=\))', basename)
        return ret[-1] if ret else ''

    def to_task(self):
        return {
            'type': 'ice',
            'name': self.name,
            'pkg_url': settings.MAIN_URL + self.package.url,
            'dir_name': self.dir_name,
            'pkg_dest_dir': '',
        }

    def push_tasks(self, priority=1):
        task = self.to_task()
        task['identifier'] = self.get_uuid_str()
        task['priority'] = priority
        nodes = self.center.iceservicenode_set.all()
        for node in nodes:
            try:
                node.push_task(copy.deepcopy(task))
            except Exception:
                errlog.exception('push task error %s' % self.name)

    def deploy(self):
        admin = self.center.get_admin()
        try:
            admin.initialize()
        except RuntimeError:
            return
        else:
            descriptor_new = admin.xml_to_app_descriptor(self.xml.path)
            if admin.application_exist(self.name):
                descriptor_old = admin.get_application_descriptor(self.name)
                if descriptor_new != descriptor_old:
                    admin.sync_application(descriptor_new)
                nodes = []
                for node in descriptor_new.nodes.values():
                    nodes.append(node.serverInstances[0].parameterValues['id'])
                for server in nodes:
                    try:
                        admin.stop_server(server)
                    except Exception:
                        errlog.exception('ice node stop error')
                    try:
                        admin.start_server(server)
                    except Exception:
                        errlog.exception('ice node start error')
            else:
                admin.add_application(descriptor_new)
                nodes = admin.get_application_nodes_from_descriptor(descriptor_new)
                for node_id in nodes:
                    try:
                        admin.start_server(node_id)
                    except Exception:
                        errlog.exception('ice node start error')
                return True
        finally:
            admin.destroy()

    def sync_application_without_restart(self):
        admin = self.center.get_admin()
        try:
            admin.initialize()
        except RuntimeError:
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
        except RuntimeError:
            return
        else:
            return admin.remove_application(self.name)
        finally:
            admin.destroy()

    def start_server(self, server_id):
        admin = self.center.get_admin()
        try:
            admin.initialize()
        except RuntimeError:
            return
        else:
            return admin.start_server(server_id)
        finally:
            admin.destroy()

    def stop_server(self, server_id):
        admin = self.center.get_admin()
        try:
            admin.initialize()
        except RuntimeError:
            return
        else:
            return admin.stop_server(server_id)
        finally:
            admin.destroy()

    def restart_server(self, server_id):
        admin = self.center.get_admin()
        try:
            admin.initialize()
        except RuntimeError:
            return
        else:
            admin.stop_server(server_id)
            admin.start_server(server_id)
        finally:
            admin.destroy()

    def get_application_nodes(self):
        admin = self.center.get_admin()
        try:
            admin.initialize()
        except RuntimeError:
            return
        else:
            return admin.get_application_nodes(self.name)
        finally:
            admin.destroy()

    def get_absolute_url(self):
        return '/services/ice-service/%s' % self.id

    def get_update_url(self):
        return '/services/ice-service/update/%s/' % self.id

    def get_delete_url(self):
        return '/services/ice-service/delete/%s/' % self.id

    def __unicode__(self):
        return self.name


# These two auto-delete files from filesystem when they are unneeded
@receiver(models.signals.post_delete, sender=IceService)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding 'IceService' object is deleted.
    """
    if instance.package:
        if os.path.isfile(instance.package.path):
            os.remove(instance.package.path)


@receiver(models.signals.pre_save, sender=IceService)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding 'IceService' object is changed.
    """
    if not instance.pk:
        return False
    try:
        old_file = IceService.objects.get(pk=instance.pk).package
    except IceService.DoesNotExist:
        return False

    new_file = instance.package
    if not old_file == new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)


class Script(models.Model):
    name = models.CharField(max_length=48, unique=True, verbose_name='名称')
    script = models.FileField(upload_to='scripts', verbose_name='脚本文件')
    server = models.ForeignKey(Server, verbose_name='运行位置')
    owner = models.ForeignKey(User, verbose_name='创建人')
    identifier = models.UUIDField(default=uuid.uuid4, editable=False, verbose_name='标识')
    note = models.TextField(blank=True, null=True, verbose_name='描述')

    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '脚本'
        verbose_name_plural = '脚本列表'
        permissions = (
            ("run_script", "Can run script"),
        )

    def filename(self):
        return os.path.basename(self.script.name)

    def to_task(self):
        return {
            'type': 'script',
            'name': self.name,
            'script_url': settings.MAIN_URL + self.script.url,
        }

    def push_task(self, priority=1):
        """ Push task to node for run
        :param priority: task priority
        """
        node = connect_node(self.server.listen_ip)
        task_param = self.to_task()
        task_param['identifier'] = self.identifier.get_hex()
        task_param['priority'] = priority
        node.add_task(task_param)

    def get_absolute_url(self):
        return '/services/script/%s' % self.id

    def get_update_url(self):
        return '/services/script/update/%s/' % self.id

    def get_delete_url(self):
        return '/services/script/delete/%s/' % self.id

    def __unicode__(self):
        return 'script: %s' % self.name


@receiver(models.signals.post_delete, sender=Script)
def auto_delete_script_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding 'Script' object is deleted.
    """
    if instance.script:
        if os.path.isfile(instance.script.path):
            os.remove(instance.script.path)
