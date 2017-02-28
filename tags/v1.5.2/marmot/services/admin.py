# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from guardian.admin import GuardedModelAdmin
from .models import (
    IceServiceCenter, IceServiceNode, IceServiceJar, IceServiceConfig, IceService, Script,
    TomcatServer, TomcatApp, TomcatAppWar, TomcatAppSql
)


@admin.register(IceServiceCenter)
class IceServiceCenterAdmin(GuardedModelAdmin):
    list_display = ['name', 'master_server_ip', 'create_time']

    def master_server_ip(self, obj):
        return obj.master_server.ip
    master_server_ip.short_description = 'ip(主)'


@admin.register(IceServiceNode)
class IceServiceNodeAdmin(admin.ModelAdmin):
    list_display = ['name', 'center__name', 'host__hostname', 'create_time']

    def center__name(self, obj):
        return obj.center.name
    center__name.short_description = '注册中心'

    def host__hostname(self, obj):
        return obj.host.hostname
    host__hostname.short_description = '主机'


@admin.register(IceServiceJar)
class IceServiceJarAdmin(admin.ModelAdmin):
    list_display = ['ice_service__name', 'url', 'active', 'create_time']

    def ice_service__name(self, obj):
        return obj.ice_service.name
    ice_service__name.short_description = 'ICE服务'


@admin.register(IceServiceConfig)
class IceServiceConfigAdmin(admin.ModelAdmin):
    list_display = ['ice_service__name', 'config', 'active', 'create_time']

    def ice_service__name(self, obj):
        return obj.ice_service.name
    ice_service__name.short_description = 'ICE服务'


@admin.register(IceService)
class IceServiceAdmin(admin.ModelAdmin):
    list_display = ['center__ip', 'name', 'version', 'user', 'deployed', 'create_time']

    def center__ip(self, obj):
        return obj.center.master_server.ip
    center__ip.short_description = '主注册中心ip'


@admin.register(TomcatServer)
class TomcatServerAdmin(GuardedModelAdmin):
    list_display = ['name', 'host']


@admin.register(TomcatApp)
class TomcatAppAdmin(admin.ModelAdmin):
    list_display = ['name', 'tomcat_server', 'user']


@admin.register(TomcatAppWar)
class TomcatAppWarAdmin(admin.ModelAdmin):
    list_display = ['url', 'tomcat_app', 'get_state_display']


@admin.register(TomcatAppSql)
class TomcatAppSqlAdmin(admin.ModelAdmin):
    list_display = ['sql__name', 'tomcat_app', 'get_state_display', 'note', 'create_time']

    def sql__name(self, obj):
        return obj.sql.name
    sql__name.short_description = 'sql文件名'

    def get_state_display(self, obj):
        return obj.get_state_display()
    get_state_display.short_description = '状态'


@admin.register(Script)
class ScriptAdmin(admin.ModelAdmin):
    list_display = ['name', 'script', 'server', 'owner', 'create_time']
