# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from guardian.admin import GuardedModelAdmin
from .models import (
    IceServiceCenter, IceServiceJar, IceServiceConfig, IceService,
    TomcatGroup, TomcatCluster, TomcatServer, TomcatApp, TomcatAppWar,
    TomcatAppSql, TomcatAppDB, TomcatAppNode, TomcatServerWarDir
)


@admin.register(IceServiceCenter)
class IceServiceCenterAdmin(GuardedModelAdmin):
    list_display = ['id', 'name', 'master_server_ip', 'create_time']

    def master_server_ip(self, obj):
        return obj.master_server.ip
    master_server_ip.short_description = 'ip(主)'


@admin.register(IceServiceJar)
class IceServiceJarAdmin(admin.ModelAdmin):
    list_display = ['id', 'ice_service__name', 'url', 'active', 'create_time']

    def ice_service__name(self, obj):
        return obj.ice_service.name
    ice_service__name.short_description = 'ICE服务'


@admin.register(IceServiceConfig)
class IceServiceConfigAdmin(admin.ModelAdmin):
    list_display = ['id', 'ice_service__name', 'config', 'active', 'create_time']

    def ice_service__name(self, obj):
        return obj.ice_service.name
    ice_service__name.short_description = 'ICE服务'


@admin.register(IceService)
class IceServiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'center__ip', 'name', 'version', 'deployed', 'get_users_display', 'create_time']

    def center__ip(self, obj):
        return obj.center.master_server.ip
    center__ip.short_description = '主注册中心ip'

    def get_users_display(self, obj):
        return obj.get_users_display()
    get_users_display.short_description = '开发者'


@admin.register(TomcatGroup)
class TomcatGroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'note', 'create_time']


@admin.register(TomcatCluster)
class TomcatClusterAdmin(GuardedModelAdmin):
    list_display = ['id', 'name', 'note', 'group__name', 'create_time']

    def group__name(self, obj):
        return obj.group.name
    group__name.short_description = 'Tomcat组'


@admin.register(TomcatServer)
class TomcatServerAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'host', 'cmd']


@admin.register(TomcatServerWarDir)
class TomcatServerWarDirAdmin(admin.ModelAdmin):
    list_display = ['id', 'war_dir', 'note', 'tomcat_server']


@admin.register(TomcatApp)
class TomcatAppAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'cluster', 'get_users_display']

    def get_users_display(self, obj):
        return obj.get_users_display()
    get_users_display.short_description = '开发者'


@admin.register(TomcatAppNode)
class TomcatAppNodeAdmin(admin.ModelAdmin):
    list_display = ['id', 'app', 'server', 'war_dir']


@admin.register(TomcatAppWar)
class TomcatAppWarAdmin(admin.ModelAdmin):
    list_display = ['id', 'url', 'tomcat_app', 'get_state_display']


@admin.register(TomcatAppDB)
class TomcatAppDBAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'ip', 'port', 'app']


@admin.register(TomcatAppSql)
class TomcatAppSqlAdmin(admin.ModelAdmin):
    list_display = ['id', 'sql__name', 'get_state_display', 'note', 'tomcat_app', 'create_time']

    def sql__name(self, obj):
        return obj.sql.name
    sql__name.short_description = 'sql文件名'

    def get_state_display(self, obj):
        return obj.get_state_display()
    get_state_display.short_description = '状态'
