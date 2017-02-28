# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from guardian.admin import GuardedModelAdmin
from django.contrib import admin
from .models import (
             StormCluster,
             StormNode,
             StormNodeJarDir,
             StormApp,
             StormAppNode,
             StormAppJar,
)

# Register your models here.
@admin.register(StormCluster)
class StormClusterAdmin(GuardedModelAdmin):
    list_display = ['id', 'name', 'note', 'create_time']

@admin.register(StormNode)
class StormNodeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name','type']

@admin.register(StormNodeJarDir)
class StormNodeJarDirAdmin(admin.ModelAdmin):
    list_display = ['id', 'jar_dir', 'note', 'storm_node']

@admin.register(StormApp)
class StormAppAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'cluster', 'args', 'main_function', 'get_users_display']

    def get_users_display(self, obj):
        return obj.get_users_display()
    get_users_display.short_description = '开发者'

@admin.register(StormAppNode)
class StormAppNodeAdmin(admin.ModelAdmin):
    list_display = ['id', 'app', 'node', 'jar_dir']

@admin.register(StormAppJar)
class StormAppJarAdmin(admin.ModelAdmin):
    list_display = ['id', 'url', 'storm_app', 'get_state_display']



