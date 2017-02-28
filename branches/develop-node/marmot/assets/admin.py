# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from assets.models import Tag, Idc, Cabinet, Server, NetCard, NetworkDevice


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'alias')


@admin.register(Idc)
class IdcAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'contact', 'phone')


@admin.register(Cabinet)
class CabinetAdmin(admin.ModelAdmin):
    list_display = ('idc__name', 'num', 'total_capacity', 'used_capacity')

    def idc__name(self, obj):
        return obj.idc.name
    idc__name.short_description = '机房'


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ('cabinet__num', 'hostname', 'ip', 'os', 'manufacturer', 'product_model')
    list_filter = ('cabinet__num', 'hostname')
    search_fields = ('hostname', 'ip')

    def cabinet__num(self, obj):
        return obj.cabinet.num
    cabinet__num.short_description = '机柜'


@admin.register(NetCard)
class NetCardAdmin(admin.ModelAdmin):
    list_display = ('server__name', 'name', 'ip_addr', 'mac_addr')

    def server__name(self, obj):
        return obj.idc.hostname
    server__name.short_description = '主机'


@admin.register(NetworkDevice)
class NetworkDeviceAdmin(admin.ModelAdmin):
    list_display = ('cabinet__num', 'num', 'type', 'position', 'manufacturer', 'model')
    list_filter = ('type',)

    def cabinet__num(self, obj):
        return obj.cabinet.num
    cabinet__num.short_description = '机柜'
