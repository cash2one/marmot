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
