# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.forms import ModelForm
from django.forms.widgets import NumberInput, TextInput, Textarea, HiddenInput, CheckboxInput

from .models import Idc, Cabinet, Server, NetworkDevice, NetCard


class IdcForm(ModelForm):
    class Meta:
        model = Idc
        exclude = ['create_time', 'modify_time']
        widgets = {
            'note': Textarea(attrs={'rows': 3}),
        }


class CabinetForm(ModelForm):
    class Meta:
        model = Cabinet
        exclude = ['create_time', 'modify_time']
        widgets = {
            'idc': HiddenInput(),
            'note': Textarea(attrs={'rows': 3}),
        }


class ServerForm(ModelForm):
    class Meta:
        model = Server
        exclude = ['create_time', 'modify_time', 'md5']
        widgets = {
            'cabinet': HiddenInput(),
            'hostname': TextInput(attrs={'readonly': True}),
            'os':  TextInput(attrs={'readonly': True}),
            'listen_ip': TextInput(attrs={'readonly': True}),
            'server_serial': TextInput(attrs={'readonly': True}),
            'ganglia': TextInput(attrs={'placeholder': 'ganglia监控系统的地址'}),
            'manufacturer': TextInput(attrs={'readonly': True}),
            'product_model': TextInput(attrs={'readonly': True}),
            'cpu_model': TextInput(attrs={'readonly': True}),
            'cpu_cores': NumberInput(attrs={'readonly': True}),
            'cpu_logic_nums': NumberInput(attrs={'readonly': True}),
            'mem_size': TextInput(attrs={'readonly': True}),
            'disk_size': TextInput(attrs={'readonly': True}),
            'allow_ports': Textarea(attrs={'rows': 3, 'placeholder': '表示已经被监听，不能处于空闲状态的端口(多个端口用英文逗号分割)'}),
            'deny_ports': Textarea(attrs={'rows': 3, 'placeholder': '不能被占用的端口(多个端口用英文逗号分割)'}),
            'cpu_level': NumberInput(attrs={'min': 50, 'max': 99, 'placeholder': '输入范围[50, 99] 单位 - %'}),
            'memory_level': NumberInput(attrs={'min': 50, 'max': 90, 'placeholder': '输入范围[40, 99] 单位 - %'}),
            'disk_level': NumberInput(attrs={'min': 50, 'max': 90, 'placeholder': '输入范围[40, 99] 单位 - %'}),
            'alarm_interval': NumberInput(attrs={'min': 5, 'max': 240, 'placeholder': '单位 - 分钟'}),
            'monitor_enabled': CheckboxInput(),
            'note': Textarea(attrs={'rows': 3}),
        }

    def clean_allow_ports(self):
        ports = self.cleaned_data["allow_ports"]
        if not ports:
            return ports
        if not ports.replace(',', '').isdigit():
            raise forms.ValidationError('端口号应为数字，多个端口之间用\",\"分割')
        ports = filter(lambda x: x != '', ports.split(','))
        port_list = filter(lambda x: not (1 < int(x) < 65535), ports)
        if port_list:
            raise forms.ValidationError('端口号应在[1, 65535]范围内: %s' % ','.join(port_list))
        return ','.join(ports)

    def clean_deny_ports(self):
        ports = self.cleaned_data["deny_ports"]
        if not ports:
            return ports
        if not ports.replace(',', '').isdigit():
            raise forms.ValidationError('端口号应为数字，多个端口之间用\",\"分割')
        ports = filter(lambda x: x != '', ports.split(','))
        port_list = filter(lambda x: not (1 < int(x) < 65535), ports)
        if port_list:
            raise forms.ValidationError('端口号应在[1, 65535]范围内: %s' % ','.join(port_list))
        return ','.join(ports)

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


class NetworkDeviceForm(ModelForm):
    class Meta:
        model = NetworkDevice
        exclude = ['create_time', 'modify_time']
        widgets = {
            'cabinet': HiddenInput(),
            'note': Textarea(attrs={'rows': 3}),
        }


class NetCardForm(ModelForm):
    class Meta:
        model = NetCard
        exclude = ['create_time', 'modify_time', 'md5']
