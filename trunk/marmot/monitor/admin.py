# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from .models import (
    RedisClusterMonitor, RedisNode,
    HBaseClusterMonitor, ESMonitor, Neo4jMonitor,
    IceGridMonitor, ActiveMqMonitor, SpringCloudMonitor,
    KafkaMonitor
)


@admin.register(RedisClusterMonitor)
class RedisClusterMonitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'active', 'note', 'created_by', 'create_time']


@admin.register(RedisNode)
class RedisNodeAdmin(admin.ModelAdmin):
    list_display = ['host', 'port', 'role', 'cluster', 'created_by', 'create_time']


@admin.register(HBaseClusterMonitor)
class HBaseClusterMonitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'host', 'active', 'note', 'created_by', 'create_time']


@admin.register(ESMonitor)
class ESMonitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'host', 'addr', 'active', 'note', 'created_by', 'create_time']


@admin.register(Neo4jMonitor)
class Neo4jMonitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'host', 'port', 'active', 'note', 'created_by', 'create_time']


@admin.register(IceGridMonitor)
class IceGridMonitorAdmin(admin.ModelAdmin):
    list_display = ['id', 'center', 'master', 'slave', 'nodes', 'active', 'note']


@admin.register(ActiveMqMonitor)
class ActiveMqMonitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'addr', 'level', 'active', 'note', 'created_by', 'create_time']


@admin.register(SpringCloudMonitor)
class SpringCloudMonitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'addr', 'port', 'active', 'note', 'created_by', 'create_time']


@admin.register(KafkaMonitor)
class KafkaMonitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'addr', 'ids', 'replicas', 'isr', 'active', 'note', 'created_by', 'create_time']
