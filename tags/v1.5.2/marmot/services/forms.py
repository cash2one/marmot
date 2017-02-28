# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import re

from django import forms
from django.forms import ModelForm
from django.forms.widgets import Textarea, HiddenInput, PasswordInput

from utils import connect_node
from .models import (
    IceServiceCenter, IceServiceNode, IceServiceJar, IceServiceConfig, IceService, Script,
    TomcatApp, TomcatServer, TomcatServerWarDir, TomcatAppSql, TomcatAppWar
)
from .tasks import download_ice_jar, download_war


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

    def clean_url(self):
        url = self.cleaned_data['url']
        base, ext = os.path.splitext(url)
        if ext != '.jar':
            raise forms.ValidationError('地址有误！请提供可以下载的jar包地址')
        return url

    def save(self, commit=True):
        instance = super(IceServiceJarForm, self).save(commit=commit)
        if 'url' in self.changed_data:
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


class TomcatServerForm(ModelForm):
    class Meta:
        model = TomcatServer
        exclude = ['create_time']

    def clean_port(self):
        port = self.cleaned_data['port']
        if not 0 < port <= 65535:
            raise forms.ValidationError('端口范围应该在[0, 65535]')
        return port


class TomcatServerWarDirForm(ModelForm):
    class Meta:
        model = TomcatServerWarDir
        fields = ['tomcat_server', 'war_dir', 'note']
        widgets = {
            'tomcat_server': HiddenInput(),
        }
        labels = {
            'war_dir': 'war包目录(填写绝对路径)'
        }

    def clean_war_dir(self):
        war_dir = self.cleaned_data['war_dir']
        ts = self.cleaned_data['tomcat_server']
        tomcat_dir = os.path.sep.join(ts.cmd.split(os.path.sep)[:3])
        if tomcat_dir != os.path.sep.join(war_dir.split(os.path.sep)[:3]):
            raise forms.ValidationError('请设置在此tomcat-server下的目录!')
        node = connect_node(ts.host.ip)
        try:
            if not node.path_exists(war_dir):
                if not node.create_path(war_dir):
                    raise forms.ValidationError('在Tomcat-Sserver下创建目录失败, marmot可能缺少权限!')
        except IOError:
            raise forms.ValidationError('连接不上Tomcat-server的服务器, 无法验证和创建目录!')
        return war_dir


class TomcatAppForm(ModelForm):
    class Meta:
        model = TomcatApp
        exclude = ['create_time', 'identifier', 'bak_flag']
        widgets = {
            'tomcat_server': HiddenInput(),
            'user': HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super(TomcatAppForm, self).__init__(*args, **kwargs)
        if 'initial' in kwargs:
            self.fields['war_dir'].queryset = TomcatServerWarDir.objects.filter(
                tomcat_server=kwargs['initial']['tomcat_server']
            )

    def clean_name(self):
        name = self.cleaned_data['name']
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            raise forms.ValidationError('只能输入字母、数字和下划线')
        return name

    def clean_port(self):
        port = self.cleaned_data['db_port']
        if not 0 < port <= 65535:
            raise forms.ValidationError('端口范围应该在[0, 65535]')
        return port


class TomcatAppWarForm(ModelForm):
    class Meta:
        model = TomcatAppWar
        exclude = ['create_time', 'package', 'state']
        widgets = {
            'tomcat_app': HiddenInput(),
        }

    def clean_url(self):
        url = self.cleaned_data['url']
        base, ext = os.path.splitext(url)
        if ext != '.war':
            raise forms.ValidationError('地址有误！请提供war包地址')
        return url

    def save(self, commit=True):
        instance = super(TomcatAppWarForm, self).save(commit=commit)
        if 'url' in self.changed_data:
            download_war.delay(instance.url, instance.id)
        return instance


class TomcatAppSqlForm(ModelForm):
    class Meta:
        model = TomcatAppSql
        exclude = ['create_time', 'state', 'sys_bak']
        widgets = {
            'tomcat_app': HiddenInput(),
        }

    def clean_sql(self):
        sql = str(self.cleaned_data['sql'])
        if sql[-4:] != '.sql':
            raise forms.ValidationError('文件格式错误, 请上传sql文件!')
        return self.cleaned_data['sql']


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
