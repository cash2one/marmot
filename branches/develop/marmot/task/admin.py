# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Task, TaskFirewall, FirewallGoal


@admin.register(FirewallGoal)
class TaskFirewallGoalAdmin(admin.ModelAdmin):
    model = FirewallGoal
    list_display = ['src_addr', 'dest_addr', 'ports']


@admin.register(TaskFirewall)
class TaskFirewallAdmin(admin.ModelAdmin):
    model = TaskFirewall
    list_display = ['create_time']
    verbose_name_plural = '防火墙任务'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    model = Task
    list_display = ['name', 'applicant', 'operator', 'content_type', 'state', 'done', 'deploy']
    verbose_name_plural = '任务'
