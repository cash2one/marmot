# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import NodeApp, NodeSrcPkg


@admin.register(NodeApp)
class ScriptAdmin(admin.ModelAdmin):
    list_display = ['name', 'server', 'cwd', 'note', 'created_by', 'create_time']


@admin.register(NodeSrcPkg)
class NodeSrcPkgAdmin(admin.ModelAdmin):
    list_display = ['id', 'app', 'package', 'note', 'created_by', 'create_time']
    ordering = ('app', 'id')
