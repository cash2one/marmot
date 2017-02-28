# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django import forms
from django.forms import ModelForm
from django.forms.widgets import (
    NumberInput, TextInput, Textarea, HiddenInput, CheckboxInput,
    CheckboxSelectMultiple
)

from utils.node_proxy import NodeProxy
from .models import Idc, Cabinet, Server, ProcessMonitor, NetworkDevice, NetCard


class IdcForm(ModelForm):
    class Meta:
        model = Idc
        exclude = ['create_time']
        widgets = {
            'note': Textarea(attrs={'rows': 3}),
        }


class CabinetForm(ModelForm):
    class Meta:
        model = Cabinet
        exclude = ['create_time']
        widgets = {
            'idc': HiddenInput(),
            'note': Textarea(attrs={'rows': 3}),
        }


class ServerCheckForm(forms.Form):
    ip = forms.GenericIPAddressField(label='IP地址')

    def clean_ip(self):
        ip = self.cleaned_data['ip']
        node = NodeProxy(ip, settings.NODE_PORT)
        try:
            if not node.is_alive():
                raise forms.ValidationError('该主机不在线')
        except IOError:
            raise forms.ValidationError('该主机不在线')
        if Server.objects.filter(ip=ip).exists():
            raise forms.ValidationError('该主机已添加')
        return ip


class ServerForm(ModelForm):
    class Meta:
        model = Server
        exclude = ['create_time', 'md5']
        widgets = {
            'tags': CheckboxSelectMultiple(),
            'cabinet': HiddenInput(),
            'hostname': TextInput(attrs={'readonly': True}),
            'os':  TextInput(attrs={'readonly': True}),
            'ip': TextInput(attrs={'readonly': True}),
            'serial_num': TextInput(attrs={'readonly': True}),
            'manufacturer': TextInput(attrs={'readonly': True}),
            'product_model': TextInput(attrs={'readonly': True}),
            'cpu_model': TextInput(attrs={'readonly': True}),
            'cpu_logic_nums': NumberInput(attrs={'readonly': True}),
            'mem_size': TextInput(attrs={'readonly': True}),
            'disk_size': TextInput(attrs={'readonly': True}),
            'cpu_level': NumberInput(attrs={'min': 50, 'max': 99, 'placeholder': '输入范围[50, 99] 单位 - %'}),
            'memory_level': NumberInput(attrs={'min': 50, 'max': 90, 'placeholder': '输入范围[40, 99] 单位 - %'}),
            'disk_level': NumberInput(attrs={'min': 50, 'max': 90, 'placeholder': '输入范围[40, 99] 单位 - %'}),
            'alarm_interval': NumberInput(attrs={'min': 5, 'max': 240, 'placeholder': '单位 - 分钟'}),
            'monitor_enabled': CheckboxInput(),
            'note': Textarea(attrs={'rows': 3}),
        }

    def clean_cpu_level(self):
        cpu_level = self.cleaned_data['cpu_level']
        if not (50 <= cpu_level <= 99):
            raise forms.ValidationError('输入范围[50, 99]')
        return cpu_level

    def clean_memory_level(self):
        memory_level = self.cleaned_data['memory_level']
        if not (40 <= memory_level <= 90):
            raise forms.ValidationError('输入范围[40, 90]')
        return memory_level

    def clean_disk_level(self):
        disk_level = self.cleaned_data['disk_level']
        if not (40 <= disk_level <= 90):
            raise forms.ValidationError('输入范围[40, 90]')
        return disk_level

    def clean_alarm_interval(self):
        alarm_interval = self.cleaned_data['alarm_interval']
        if not (5 <= alarm_interval <= 240):
            raise forms.ValidationError('输入范围[5, 240]')
        return alarm_interval


class ProcessMonitorForm(ModelForm):
    class Meta:
        model = ProcessMonitor
        exclude = ['create_time']
        widgets = {
            'server': HiddenInput(),
        }

    def clean_port(self):
        port = self.cleaned_data['port']
        if not (1 <= port <= 65535):
            raise forms.ValidationError('输入范围[1, 65535]')
        return port

    def clean_cmd(self):
        cmd = self.cleaned_data['cmd']
        server = self.cleaned_data['server']
        node = NodeProxy(server.ip, settings.NODE_PORT)
        try:
            if not node.path_exists(cmd):
                raise forms.ValidationError('应用路径在目标服务器上不存在!')
        except IOError:
            raise forms.ValidationError('无法连接上服务器, 无法验证应用路径!')
        return cmd


class NetworkDeviceForm(ModelForm):
    class Meta:
        model = NetworkDevice
        exclude = ['create_time']
        widgets = {
            'cabinet': HiddenInput(),
            'note': Textarea(attrs={'rows': 3}),
        }


class NetCardForm(ModelForm):
    class Meta:
        model = NetCard
        exclude = ['create_time']
