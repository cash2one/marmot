# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import re
import xmlrpclib
import httplib
import hashlib

from django import forms
from django.forms import ModelForm
from django.forms.widgets import Textarea, HiddenInput, SelectMultiple, MultipleHiddenInput
from django.contrib.auth.models import User
from django.conf import settings

from utils.node_proxy import NodeProxy

from .models import (
    IceServiceCenter, IceServiceJar, IceServiceConfig, IceService,
    TomcatGroup, TomcatCluster, TomcatServer, TomcatServerWarDir,
    TomcatApp, TomcatAppSql, TomcatAppWar, TomcatAppDB
)
from .tasks import download_ice_jar, download_war


class IceServiceCenterForm(ModelForm):
    class Meta:
        model = IceServiceCenter
        exclude = ['create_time', 'modify_time']
        widgets = {
            'note': Textarea(attrs={'rows': 3}),
        }


class IceServiceJarForm(ModelForm):
    class Meta:
        model = IceServiceJar
        exclude = ['create_time', 'modify_time', 'package', 'state', 'md5']
        widgets = {
            'active': HiddenInput(),
            'ice_service': HiddenInput(),
            'user': HiddenInput(),
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
        exclude = ['create_time', 'modify_time', 'md5']
        widgets = {
            'active': HiddenInput(),
            'ice_service': HiddenInput(),
            'user': HiddenInput(),
        }

    def clean_config(self):
        config = str(self.cleaned_data['config'])
        if config[-4:] != '.zip':
            raise forms.ValidationError('文件格式错误, 请上传zip文件!')
        return self.cleaned_data['config']
    
    def save(self, commit=True):
        instance = super(IceServiceConfigForm, self).save(commit=commit)
        if os.path.isfile(instance.config.path):
            instance.md5 = hashlib.md5(open(instance.config.path, 'rb').read()).hexdigest()
            instance.save()
        return instance


class IceServiceForm(ModelForm):
    class Meta:
        model = IceService
        exclude = ['create_time', 'modify_time', 'deployed']
        widgets = {
            'center': HiddenInput(),
            'users': MultipleHiddenInput(),
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


class IceServiceUpdateForm(IceServiceForm):
    users = forms.ModelMultipleChoiceField(
        required=True, label='开发者', queryset=User.objects.filter(profile__role__alias='developer').all()
    )

    class Meta:
        model = IceService
        exclude = ['create_time', 'modify_time', 'deployed']
        widgets = {
            'center': HiddenInput(),
        }


class TomcatGroupForm(ModelForm):
    class Meta:
        model = TomcatGroup
        exclude = ['create_time']


class TomcatClusterForm(ModelForm):
    class Meta:
        model = TomcatCluster
        exclude = ['create_time']
        widgets = {
            'group': HiddenInput(),
            'user': HiddenInput(),
        }


class TomcatServerForm(ModelForm):
    class Meta:
        model = TomcatServer
        exclude = ['create_time']
        widgets = {
            'cluster': HiddenInput(),
            'user': HiddenInput(),
        }

    def clean_port(self):
        port = self.cleaned_data['port']
        if not 0 < port <= 65535:
            raise forms.ValidationError('端口范围应该在[0, 65535]')
        return port

    def clean_cmd(self):
        host = self.cleaned_data['host']
        cmd = self.cleaned_data['cmd']
        node = NodeProxy(self.cleaned_data['host'].ip, settings.NODE_PORT)
        try:
            if not node.path_exists(cmd):
                raise forms.ValidationError('该启动命令不存在!')
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            raise forms.ValidationError('连接不上服务器, 无法验证启动命令的正确性！')
        if TomcatServer.objects.filter(host=host, cmd=cmd).exists():
            if self.instance.pk is None:
                raise forms.ValidationError('该Tomcat已经添加过了')
            else:
                if TomcatServer.objects.get(host=host, cmd=cmd).id != self.instance.id:
                    raise forms.ValidationError('该Tomcat已经添加过了')
        return cmd


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
            raise forms.ValidationError('请设置在此Tomcat下的目录!')
        node = NodeProxy(ts.host.ip, settings.NODE_PORT)
        try:
            if not node.path_exists(war_dir):
                if not node.create_path(war_dir):
                    raise forms.ValidationError('在Tomcat下创建目录失败, marmot可能缺少权限!')
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            raise forms.ValidationError('连接不上此Tomcat的服务器, 无法验证和创建目录!')
        return war_dir


class TomcatAppForm(forms.Form):
    cluster = forms.ModelChoiceField(queryset=TomcatCluster.objects.all(), widget=forms.HiddenInput)
    name = forms.CharField(max_length=48, label='名称')
    servers = forms.ModelMultipleChoiceField(queryset=TomcatServer.objects.all(), label='节点',
                                             widget=forms.CheckboxSelectMultiple)
    note = forms.CharField(max_length=255, required=False, label='说明', widget=forms.Textarea)

    def clean_name(self):
        name = self.cleaned_data['name']
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            raise forms.ValidationError('只能输入字母、数字和下划线')
        return name


class TomcatAppUpdateForm(TomcatAppForm):
    users = forms.ModelMultipleChoiceField(
        required=True, label='开发者', queryset=User.objects.filter(profile__role__alias='developer').all()
    )


class TomcatAppWarForm(ModelForm):
    class Meta:
        model = TomcatAppWar
        exclude = ['create_time', 'package', 'state', 'md5']
        widgets = {
            'tomcat_app': HiddenInput(),
            'user': HiddenInput(),
            'active': HiddenInput(),
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


class TomcatAppDBForm(ModelForm):
    class Meta:
        model = TomcatAppDB
        exclude = ['state']
        widgets = {
            'app': HiddenInput(),
        }

    def clean_port(self):
        port = self.cleaned_data['port']
        if not 0 < port <= 65535:
            raise forms.ValidationError('端口范围应该在(0, 65535]')
        return port


class TomcatAppSqlForm(ModelForm):
    class Meta:
        model = TomcatAppSql
        exclude = ['create_time', 'state', 'sys_bak']
        widgets = {
            'tomcat_app': HiddenInput(),
            'user': HiddenInput(),
        }

    def clean_sql(self):
        sql = str(self.cleaned_data['sql'])
        if sql[-4:] != '.sql':
            raise forms.ValidationError('文件格式错误, 请上传sql文件!')
        return self.cleaned_data['sql']
