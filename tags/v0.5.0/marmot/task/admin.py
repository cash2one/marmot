# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Task, TaskFirewall


@admin.register(TaskFirewall)
class TaskFirewallAdmin(admin.ModelAdmin):
    model = TaskFirewall
    list_display = ['src_addr', 'dest_addr', 'ports']
    verbose_name_plural = '防火墙任务'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    model = Task
    list_display = ['name', 'applicant', 'operator', 'type', 'progress', 'done', 'deploy']
    verbose_name_plural = '任务'
