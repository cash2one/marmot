# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Task, TaskFirewall, FirewallGoal


@admin.register(FirewallGoal)
class TaskFirewallGoalAdmin(admin.ModelAdmin):
    list_display = ['src_addr', 'dest_addr', 'ports']


@admin.register(TaskFirewall)
class TaskFirewallAdmin(admin.ModelAdmin):
    list_display = ['create_time']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'applicant', 'operator', 'content_type', 'state', 'done', 'deploy']
