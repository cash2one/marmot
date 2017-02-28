# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.forms import ModelForm

from .models import TaskIce, TaskTomcat, TaskDNS


class TaskFirewallGoalForm(forms.Form):
    src_addr = forms.CharField(max_length=64, label='源地址')
    dest_addr = forms.CharField(max_length=64, label='目标地址')
    ports = forms.CharField(max_length=255, label='端口')


class TaskFirewallForm(forms.Form):
    name = forms.CharField(max_length=64, label='任务名称')
    note = forms.CharField(max_length=255, required=False, label='说明', widget=forms.Textarea)


class TaskIceForm(ModelForm):
    class Meta:
        model = TaskIce
        exclude = ['create_time']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 3}),
        }


class TaskTomcatForm(ModelForm):
    class Meta:
        model = TaskTomcat
        exclude = ['create_time']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 3}),
        }


class TaskDNSForm(ModelForm):
    class Meta:
        model = TaskDNS
        exclude = ['create_time']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 3}),
        }
