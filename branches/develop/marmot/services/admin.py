# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from guardian.admin import GuardedModelAdmin
from .models import (
    IceServiceCenter, IceServiceNode, IceServiceJar, IceServiceConfig, IceService, Script
)


@admin.register(IceServiceCenter)
class IceServiceCenterAdmin(GuardedModelAdmin):
    model = IceServiceCenter
    list_display = ['name', 'master_server_ip', 'create_time']
    verbose_name_plural = 'ICE注册中心'

    def master_server_ip(self, obj):
        return obj.master_server.ip
    master_server_ip.short_description = 'ip(主)'


@admin.register(IceServiceNode)
class IceServiceNodeAdmin(admin.ModelAdmin):
    model = IceServiceNode
    list_display = ['name', 'center__name', 'host__hostname', 'create_time']
    verbose_name_plural = 'ICE节点'

    def center__name(self, obj):
        return obj.center.name
    center__name.short_description = '注册中心'

    def host__hostname(self, obj):
        return obj.host.hostname
    host__hostname.short_description = '主机'


@admin.register(IceServiceJar)
class IceServiceJarAdmin(admin.ModelAdmin):
    model = IceServiceJar
    list_display = ['ice_service__name', 'url', 'active', 'create_time']
    verbose_name_plural = 'ICE服务jar包'

    def ice_service__name(self, obj):
        return obj.ice_service.name
    ice_service__name.short_description = 'ICE服务'


@admin.register(IceServiceConfig)
class IceServiceConfigAdmin(admin.ModelAdmin):
    model = IceServiceConfig
    list_display = ['ice_service__name', 'config', 'active', 'create_time']
    verbose_name_plural = 'ICE服务配置文件'

    def ice_service__name(self, obj):
        return obj.ice_service.name
    ice_service__name.short_description = 'ICE服务'


@admin.register(IceService)
class IceServiceAdmin(admin.ModelAdmin):
    model = IceService
    list_display = ['center__ip', 'name', 'version', 'user', 'deployed', 'create_time']
    verbose_name_plural = 'ICE服务'

    def center__ip(self, obj):
        return obj.center.master_server.ip
    center__ip.short_description = '主注册中心ip'


@admin.register(Script)
class ScriptAdmin(admin.ModelAdmin):
    model = Script
    list_display = ['name', 'script', 'server', 'owner', 'create_time']
    verbose_name_plural = '脚本'
