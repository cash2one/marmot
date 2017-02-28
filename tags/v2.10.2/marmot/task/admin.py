# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import (
    TaskIce, TaskFirewall, FirewallGoal, TaskTomcat,
    Task, TaskDNS
)


@admin.register(FirewallGoal)
class TaskFirewallGoalAdmin(admin.ModelAdmin):
    list_display = ['src_addr', 'dest_addr', 'ports']


@admin.register(TaskFirewall)
class TaskFirewallAdmin(admin.ModelAdmin):
    list_display = ['create_time', 'name', 'note']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['create_time', 'workflowactivity', 'content_type']


@admin.register(TaskIce)
class TaskIceAdmin(admin.ModelAdmin):
    list_display = ['create_time', 'name', 'note']


@admin.register(TaskTomcat)
class TaskTomcatAdmin(admin.ModelAdmin):
    list_display = ['create_time', 'name', 'note']


@admin.register(TaskDNS)
class TaskDNSAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'domain', 'ip', 'note']
