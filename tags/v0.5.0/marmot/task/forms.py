# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from services.models import IceService


class TaskFirewallForm(forms.Form):
    name = forms.CharField(max_length=64, label='任务名称')
    src_addr = forms.CharField(max_length=128, label='源地址')
    dest_addr = forms.CharField(max_length=128, label='目标地址')
    ports = forms.CharField(max_length=255, label='端口')
    note = forms.CharField(max_length=255, required=False, label='说明', widget=forms.Textarea)


class TaskIceServiceForm(forms.Form):
    name = forms.CharField(max_length=64, label='任务名称')
    ice_service = forms.ModelChoiceField(label='ICE服务', queryset=IceService.objects.all())
    note = forms.CharField(max_length=255, required=False, label='说明', widget=forms.Textarea)
