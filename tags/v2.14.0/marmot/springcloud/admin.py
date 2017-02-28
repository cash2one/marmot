# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from .models import SpringCloudCluster, SpringCloudNode, SpringCloudApp, SpringCloudFile


@admin.register(SpringCloudCluster)
class SpringCloudClusterAdmin(GuardedModelAdmin):
    list_display = ['name', 'note', 'created_by', 'create_time']
    ordering = ('-id',)


@admin.register(SpringCloudNode)
class SpringCloudNodeAdmin(admin.ModelAdmin):
    list_display = ['name', 'server', 'cluster', 'cwd', 'note', 'created_by', 'create_time']
    ordering = ('-id', 'cluster')


@admin.register(SpringCloudApp)
class SpringCloudAppAdmin(admin.ModelAdmin):
    list_display = ['name', 'startup', 'port', 'cluster', 'note', 'created_by', 'create_time']
    ordering = ('-id', 'cluster')


@admin.register(SpringCloudFile)
class SpringCloudFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'file', 'app', 'type', 'created_by', 'create_time']
    ordering = ('-id',)
