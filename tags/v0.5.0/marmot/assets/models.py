# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import hashlib
import json

from django.db import models


class Tag(models.Model):
    name = models.CharField(max_length=32, verbose_name='名称')
    alias = models.CharField(max_length=32, unique=True, verbose_name='别名')
    note = models.TextField(blank=True, null=True, verbose_name='备注')
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
    note = models.TextField(blank=True, null=True, verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '机房'
        verbose_name_plural = '机房列表'

    def get_absolute_url(self):
        return '/assets/idc/%i' % self.id

    def get_update_url(self):
        return '/assets/idc/update/%i' % self.id

    def get_delete_url(self):
        return '/assets/idc/delete/%i' % self.id

    def get_create_cabinet_url(self):
        return '/assets/idc/%i/cabinet/create' % self.id

    def __unicode__(self):
        return self.name


class Cabinet(models.Model):
    idc = models.ForeignKey(Idc, on_delete=models.CASCADE, verbose_name='机房')
    num = models.CharField(max_length=24, unique=True, verbose_name='机柜编号')
    total_capacity = models.PositiveSmallIntegerField(verbose_name='机柜容量')
    used_capacity = models.PositiveSmallIntegerField(verbose_name='已用机柜容量')
    note = models.TextField(blank=True, null=True, verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '机柜'
        verbose_name_plural = '机柜列表'

    def get_absolute_url(self):
        return '/assets/cabinet/%s' % self.id

    def get_update_url(self):
        return '/assets/cabinet/update/%s' % self.id

    def get_delete_url(self):
        return '/assets/cabinet/delete/%s' % self.id

    def get_create_network_device_url(self):
        return '/assets/cabinet/%i/network-device/create' % self.id

    def __unicode__(self):
        return 'Cabinet: %s' % self.num


class Server(models.Model):
    USE_FOR_CHOICES = (
        ('prod', '生产'),
        ('dev', '开发'),
        ('prod/dev', '生产/开发'),
        ('others', '其他'),
    )

    cabinet = models.ForeignKey(Cabinet, on_delete=models.CASCADE, verbose_name='机柜')
    tags = models.ManyToManyField(Tag, verbose_name='标签')
    hostname = models.CharField(max_length=24, verbose_name='主机名')
    listen_ip = models.GenericIPAddressField(unique=True, verbose_name='客户端监听IP')
    os = models.CharField(max_length=32, verbose_name='操作系统')
    server_serial = models.CharField(max_length=48, verbose_name='服务器序列号')
    ganglia = models.CharField(max_length=128, blank=True, null=True, verbose_name='ganglia')
    manufacturer = models.CharField(max_length=24, verbose_name='厂商')
    product_model = models.CharField(max_length=80, verbose_name='产品型号')
    cpu_model = models.CharField(max_length=80, verbose_name='CPU型号')
    cpu_logic_nums = models.PositiveSmallIntegerField(verbose_name='CPU逻辑内核数')
    cpu_cores = models.PositiveSmallIntegerField(default=0, verbose_name='CPU物理核数')
    mem_size = models.CharField(max_length=12, verbose_name='内存大小')
    disk_size = models.CharField(max_length=12, verbose_name='硬盘大小')
    use_for = models.CharField(max_length=32, choices=USE_FOR_CHOICES, verbose_name='用途')
    allow_ports = models.TextField(blank=True, null=True, verbose_name='监听端口')
    deny_ports = models.TextField(blank=True, null=True, verbose_name='开放端口')
    md5 = models.CharField(max_length=64, blank=True, null=True, verbose_name='md5值')
    cpu_level = models.PositiveIntegerField(default=99, verbose_name='CPU负载警报线')
    memory_level = models.PositiveIntegerField(default=80, verbose_name='内存占用警报线')
    disk_level = models.PositiveIntegerField(default=80, verbose_name='硬盘使用警报线')
    alarm_interval = models.PositiveIntegerField(default=20, verbose_name='报警间隔(分钟)')
    monitor_enabled = models.BooleanField(default=False, verbose_name='开启监控')
    note = models.TextField(blank=True, null=True, verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '服务器'
        verbose_name_plural = '服务器列表'

    def __unicode__(self):
        return '%s - %s' % (self.hostname, self.listen_ip)

    def add_port(self, port):
        ports = set(self.get_ports())
        try:
            ports.add(int(port))
        except ValueError:
            return
        self.allow_ports = json.dumps(list(ports))
        self.save()

    def remove_port(self, port):
        ports = set(self.get_ports())
        try:
            ports.remove(int(port))
        except (KeyError, ValueError):
            return
        self.allow_ports = json.dumps(list(ports))
        self.save()

    def set_ports(self, ports):
        self.allow_ports = json.dumps(list(set(ports)))
        self.save()

    def get_ports(self):
        return json.loads(self.allow_ports)

    def get_monitor_enabled_display(self):
        return '开启' if self.monitor_enabled else '关闭'

    def get_absolute_url(self):
        return '/assets/server/%s' % self.id

    def get_update_url(self):
        return '/assets/server/update/%s' % self.id

    def get_delete_url(self):
        return '/assets/server/delete/%s' % self.id

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.id:
            self.cabinet.used_capacity += 1
            self.cabinet.save()
            m = hashlib.md5()
            m.update(self.hostname+self.server_serial+self.manufacturer+self.product_model)
            self.md5 = m.hexdigest()
        return super(Server, self).save(force_insert=force_insert, force_update=force_update,
                                        using=using, update_fields=update_fields)

    def delete(self, using=None):
        super(Server, self).delete(using=using)
        self.cabinet.used_capacity -= 1
        self.cabinet.save()


class NetCard(models.Model):
    server = models.ForeignKey(Server, on_delete=models.CASCADE, verbose_name='主机')
    name = models.CharField(max_length=24, verbose_name='网卡名')
    ip_addr = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP地址')
    net_addr = models.CharField(max_length=24, blank=True, null=True, verbose_name='网络地址')
    sub_mask = models.CharField(max_length=24, blank=True, null=True, verbose_name='子网掩码')
    mac_addr = models.CharField(max_length=24, verbose_name='mac地址')
    bonding = models.CharField(max_length=24, blank=True, null=True, verbose_name='bonding')

    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '网卡'
        verbose_name_plural = '网卡列表'

    def get_absolute_url(self):
        return '/assets/net-card/%s' % self.id

    def __unicode__(self):
        return '网卡名: %s; 网卡ip: %s' % (self.name, self.ip_addr)


class NetworkDevice(models.Model):
    PRODUCT_TYPE_CHOICES = (
        ('firewall', '防火墙'),
        ('switch', '交换机'),
        ('router', '路由器'),
    )

    cabinet = models.ForeignKey(Cabinet, on_delete=models.CASCADE, verbose_name='机柜')
    num = models.CharField(max_length=12, verbose_name='设备编号')
    position = models.CharField(max_length=32, verbose_name='设备位置')
    manufacturer = models.CharField(max_length=24, verbose_name='厂商')
    device_model = models.CharField(max_length=24, verbose_name='型号')
    device_type = models.CharField(max_length=24, choices=PRODUCT_TYPE_CHOICES, verbose_name='设备类型')
    note = models.TextField(blank=True, null=True, verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '网络设备'
        verbose_name_plural = '网络设备列表'

    def get_absolute_url(self):
        return '/assets/network-device/%s' % self.id

    def get_update_url(self):
        return '/assets/network-device/update/%s' % self.id

    def get_delete_url(self):
        return '/assets/network-device/delete/%s' % self.id

    def __unicode__(self):
        return '网络设备: %s' % self.num

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.id:
            self.cabinet.used_capacity += 1
            self.cabinet.save()
        return super(NetworkDevice, self).save(force_insert=force_insert, force_update=force_update,
                                               using=using, update_fields=update_fields)

    def delete(self, using=None):
        super(NetworkDevice, self).delete(using=using)
        self.cabinet.used_capacity -= 1
        self.cabinet.save()
