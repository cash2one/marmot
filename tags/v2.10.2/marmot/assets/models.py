# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import httplib
import hashlib
import xmlrpclib

from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse

from utils.node_proxy import NodeProxy


class Tag(models.Model):
    name = models.CharField(max_length=32, verbose_name='名称')
    alias = models.CharField(max_length=32, unique=True, verbose_name='别名')
    note = models.TextField(blank=True, default='', verbose_name='备注')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '主机标签'
        verbose_name_plural = '主机标签列表'

    def __unicode__(self):
        return self.name


class Idc(models.Model):
    name = models.CharField(max_length=32, verbose_name='名称')
    type = models.CharField(max_length=32, verbose_name='类型')
    addr = models.CharField(max_length=255, verbose_name='地址')
    contact = models.CharField(max_length=24, verbose_name='联系人')
    phone = models.CharField(max_length=24, verbose_name='联系电话')
    note = models.TextField(blank=True, default='', verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '机房'
        verbose_name_plural = '机房列表'

    def __unicode__(self):
        return 'IDC: %s' % self.name

    def get_absolute_url(self):
        return reverse('idc_detail', kwargs={'pk': self.id})

    def get_update_url(self):
        return reverse('idc_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('idc_delete', kwargs={'pk': self.id})


class Cabinet(models.Model):
    idc = models.ForeignKey(Idc, on_delete=models.CASCADE, verbose_name='机房')
    num = models.CharField(max_length=24, unique=True, verbose_name='编号')
    total_capacity = models.PositiveSmallIntegerField(verbose_name='容量')
    used_capacity = models.PositiveSmallIntegerField(verbose_name='已用容量')
    note = models.TextField(blank=True, default='', verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '机柜'
        verbose_name_plural = '机柜列表'

    def __unicode__(self):
        return 'Cabinet: %s' % self.num

    @property
    def is_full(self):
        return self.used_capacity >= self.total_capacity

    def get_absolute_url(self):
        return reverse('cabinet_detail', kwargs={'pk': self.id})

    def get_update_url(self):
        return reverse('cabinet_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('cabinet_delete', kwargs={'pk': self.id})


class Server(models.Model):
    USE_FOR_CHOICES = (
        ('prod', '正式'),
        ('dev', '测试'),
        ('pre', '预发布'),
        ('others', '其他'),
    )

    cabinet = models.ForeignKey(Cabinet, on_delete=models.CASCADE, verbose_name='机柜')
    tags = models.ManyToManyField(Tag, verbose_name='标签')
    hostname = models.CharField(max_length=24, verbose_name='主机名')
    ip = models.GenericIPAddressField(unique=True, verbose_name='IP')
    os = models.CharField(max_length=32, verbose_name='操作系统')
    serial_num = models.CharField(max_length=48, verbose_name='序列号')
    manufacturer = models.CharField(max_length=24, verbose_name='厂商')
    product_model = models.CharField(max_length=80, verbose_name='产品型号')
    cpu_model = models.CharField(max_length=80, verbose_name='CPU型号')
    cpu_logic_nums = models.PositiveSmallIntegerField(verbose_name='CPU逻辑内核数')
    mem_size = models.CharField(max_length=12, verbose_name='内存大小')
    disk_size = models.CharField(max_length=12, verbose_name='硬盘大小')
    use_for = models.CharField(max_length=32, choices=USE_FOR_CHOICES, verbose_name='用途')

    cpu_level = models.PositiveIntegerField(default=99, verbose_name='CPU负载警报线')
    memory_level = models.PositiveIntegerField(default=80, verbose_name='内存占用警报线')
    disk_level = models.PositiveIntegerField(default=80, verbose_name='硬盘使用警报线')
    alarm_interval = models.PositiveIntegerField(default=20, verbose_name='报警间隔(分钟)')
    monitor_enabled = models.BooleanField(default=False, verbose_name='开启监控')

    note = models.TextField(blank=True, default='', verbose_name='备注')
    md5 = models.CharField(max_length=64, blank=True, default='', verbose_name='md5值')

    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '服务器'
        verbose_name_plural = '服务器列表'

    def __unicode__(self):
        return '%s - %s' % (self.hostname, self.ip)

    @property
    def is_alive(self):
        node = NodeProxy(self.ip, settings.NODE_PORT)
        try:
            return node.is_alive()
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return False

    def get_tags_display(self):
        return '; '.join([t.name for t in self.tags.all()])

    def get_monitor_enabled_display(self):
        return '开启' if self.monitor_enabled else '关闭'

    def get_absolute_url(self):
        return reverse('server_detail', kwargs={'pk': self.id})

    def get_update_url(self):
        return reverse('server_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('server_delete', kwargs={'pk': self.id})

    def save(self, *args, **kwargs):
        if self.id is None:
            self.cabinet.used_capacity += 1
            self.cabinet.save()
            m = hashlib.md5()
            m.update(self.hostname + self.serial_num + self.manufacturer + self.product_model)
            self.md5 = m.hexdigest()
        return super(Server, self).save(*args, **kwargs)

    def delete(self, using=None):
        super(Server, self).delete(using=using)
        self.cabinet.used_capacity -= 1
        self.cabinet.save()


class ProcessMonitor(models.Model):
    server = models.ForeignKey(Server, on_delete=models.CASCADE, verbose_name='主机')
    name = models.CharField(max_length=24, verbose_name='名称')
    cmd = models.CharField(max_length=255, verbose_name='应用路径')
    port = models.PositiveIntegerField(verbose_name='端口')
    note = models.TextField(blank=True, default='', verbose_name='备注')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '监控器'
        verbose_name_plural = '监控器列表'
        unique_together = (
            ('server', 'name'),
            ('server', 'cmd'),
            ('server', 'port'),
        )

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('process_monitor_detail', kwargs={'pk': self.id})

    def get_update_url(self):
        return reverse('process_monitor_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('process_monitor_delete', kwargs={'pk': self.id})


class NetCard(models.Model):
    server = models.ForeignKey(Server, on_delete=models.CASCADE, verbose_name='主机')
    name = models.CharField(max_length=24, verbose_name='网卡名')
    ip_addr = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP地址')
    net_addr = models.CharField(max_length=24, blank=True, default='', verbose_name='网络地址')
    sub_mask = models.CharField(max_length=24, blank=True, default='', verbose_name='子网掩码')
    mac_addr = models.CharField(max_length=24, verbose_name='mac地址')

    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '网卡'
        verbose_name_plural = '网卡列表'

    def __unicode__(self):
        return 'NetCard: %s; IP: %s' % (self.name, self.ip_addr)


class NetworkDevice(models.Model):
    PRODUCT_TYPE_CHOICES = (
        ('firewall', '防火墙'),
        ('switch', '交换机'),
        ('router', '路由器'),
    )

    cabinet = models.ForeignKey(Cabinet, on_delete=models.CASCADE, verbose_name='机柜')
    num = models.CharField(max_length=12, verbose_name='编号')
    position = models.CharField(max_length=32, verbose_name='位置')
    manufacturer = models.CharField(max_length=24, verbose_name='厂商')
    model = models.CharField(max_length=24, verbose_name='型号')
    type = models.CharField(max_length=24, choices=PRODUCT_TYPE_CHOICES, verbose_name='类型')
    note = models.TextField(blank=True, default='', verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '网络设备'
        verbose_name_plural = '网络设备列表'

    def __unicode__(self):
        return 'NetworkDevice: %s' % self.num

    def get_absolute_url(self):
        return reverse('network_device_detail', kwargs={'pk': self.id})

    def get_update_url(self):
        return reverse('network_device_update', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('network_device_delete', kwargs={'pk': self.id})

    def save(self, *args, **kwargs):
        if self.id is None:
            self.cabinet.used_capacity += 1
            self.cabinet.save()
        return super(NetworkDevice, self).save(*args, **kwargs)

    def delete(self, using=None):
        super(NetworkDevice, self).delete(using=using)
        self.cabinet.used_capacity -= 1
        self.cabinet.save()
