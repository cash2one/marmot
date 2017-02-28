# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.forms import ModelForm
from django.forms.widgets import Textarea, HiddenInput

from .models import (
    IceServiceCenter, IceServiceNode, IceServiceJar, IceServiceConfig, IceService, Script
)
from .tasks import download_ice_jar


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


class IceServiceJarForm(ModelForm):
    class Meta:
        model = IceServiceJar
        exclude = ['create_time', 'modify_time', 'package', 'finished']
        widgets = {
            'active': HiddenInput(),
            'ice_service': HiddenInput(),
        }

    def save(self, commit=True):
        changed_data = self.changed_data()
        instance = super(IceServiceJarForm, self).save(commit=commit)
        if 'url' in changed_data:
            download_ice_jar.delay(instance.url, instance.id)
        return instance


class IceServiceConfigForm(ModelForm):
    class Meta:
        model = IceServiceConfig
        exclude = ['create_time', 'modify_time']
        widgets = {
            'active': HiddenInput(),
            'ice_service': HiddenInput(),
        }

    def clean_config(self):
        config = str(self.cleaned_data['config'])
        if config[-4:] != '.zip':
            raise forms.ValidationError('文件格式错误, 请上传zip文件!')
        return self.cleaned_data['config']


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
            if self.instance.pk is None:
                raise forms.ValidationError('该注册中心中, 已经存在%s' % name)
            else:
                if IceService.objects.get(center=center, name=name).id != self.instance.id:
                    raise forms.ValidationError('该注册中心中, 已经存在%s' % name)
        return name

    def clean_dir_name(self):
        center = self.cleaned_data['center']
        dir_name = self.cleaned_data['dir_name']
        if IceService.objects.filter(center=center, dir_name=dir_name).exists():
            if self.instance.pk is None:
                raise forms.ValidationError('该注册中心中, 该工程目录已经存在: %s' % dir_name)
            else:
                if IceService.objects.get(center=center, dir_name=dir_name).id != self.instance.id:
                    raise forms.ValidationError('该注册中心中, 该工程目录已经存在: %s' % dir_name)
        return dir_name


class ScriptForm(ModelForm):
    class Meta:
        model = Script
        exclude = ['create_time', 'modify_time']
        widgets = {
            'owner': HiddenInput(),
            'note': Textarea(attrs={'rows': 5}),
        }
        labels = {
            'script': '脚本文件(Shell或Python)'
        }

    def clean_script(self):
        return self.cleaned_data['script']

    def save(self, commit=True):
        print self.changed_data
        return super(ScriptForm, self).save(commit=commit)
