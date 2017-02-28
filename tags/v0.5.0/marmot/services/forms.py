# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.forms import ModelForm
from django.forms.widgets import Textarea, HiddenInput

from .models import IceServiceCenter, IceServiceNode, IceService, Script


class IceServiceCenterForm(ModelForm):
    class Meta:
        model = IceServiceCenter
        exclude = ['create_time', 'modify_time']
        widgets = {
            'note': Textarea(attrs={'rows': 3}),
        }


class IceServiceNodeForm(ModelForm):
    class Meta:
        model = IceServiceNode
        exclude = ['create_time', 'modify_time']
        widgets = {
            'center': HiddenInput(),
            'user': HiddenInput(),
            'note': Textarea(attrs={'rows': 3}),
        }


class IceServiceForm(ModelForm):
    class Meta:
        model = IceService
        exclude = ['create_time', 'modify_time', 'deployed']
        widgets = {
            'center': HiddenInput(),
            'user': HiddenInput(),
            'note': Textarea(attrs={'rows': 3}),
        }

    def clean_name(self):
        center = self.cleaned_data['center']
        name = self.cleaned_data['name']
        if IceService.objects.filter(center=center, name=name).exists():
            if not self.instance.id:
                raise forms.ValidationError('该注册中心中, 已经存在%s' % name)
            else:
                if IceService.objects.get(center=center, name=name).id != self.instance.id:
                    raise forms.ValidationError('该注册中心中, 已经存在%s' % name)
        return name

    def clean_dir_name(self):
        center = self.cleaned_data['center']
        dir_name = self.cleaned_data['dir_name']
        if IceService.objects.filter(center=center, dir_name=dir_name).exists():
            if not self.instance.id:
                raise forms.ValidationError('该注册中心中, 该工程目录已经存在: %s' % dir_name)
            else:
                if IceService.objects.get(center=center, dir_name=dir_name).id != self.instance.id:
                    raise forms.ValidationError('该注册中心中, 该工程目录已经存在: %s' % dir_name)
        return dir_name

    def clean_package(self):
        package = str(self.cleaned_data['package'])
        if package[-4:] != '.zip':
            raise forms.ValidationError('文件格式错误, 请上传zip文件!')
        return self.cleaned_data['package']


class ScriptForm(ModelForm):
    class Meta:
        model = Script
        exclude = ['create_time', 'modify_time', 'owner']
        widgets = {
            'note': Textarea(attrs={'rows': 5}),
        }
        labels = {
            'script': '脚本文件(Shell或Python)'
        }

    def clean_script(self):
        return self.cleaned_data['script']
