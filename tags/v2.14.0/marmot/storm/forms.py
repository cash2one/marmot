# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import httplib
import xmlrpclib

from django import forms
from django.forms import ModelForm
from django.forms.widgets import Textarea, HiddenInput, MultipleHiddenInput
from django.contrib.auth.models import User
from django.conf import settings

from utils.node_proxy import NodeProxy
from services.tasks import  download_storm_jar

from .models import (
         StormCluster,StormNode,StormAppJar,StormNodeJarDir         
)

class StormClusterForm(ModelForm):
    class Meta:
        model = StormCluster
        exclude = ['create_time']


class StormNodeForm(ModelForm):
    class Meta:
        model = StormNode
        exclude = ['create_time']
        widgets = {
            'cluster': HiddenInput(),
            'user': HiddenInput(),
        }
    NODE_TYPE = (
        ('nimbus','Nimbus'),
        ('supervisor','Supervisor'),
        ('ui','UI'),
    )
    type = forms.ChoiceField(choices=NODE_TYPE,label='类型')

class StormAppForm(forms.Form): 
    cluster = forms.ModelChoiceField(queryset=StormCluster.objects.all(), widget=forms.HiddenInput)
    name = forms.CharField(max_length=48, label='名称')
    nodes = forms.ModelChoiceField(queryset=StormNode.objects.all(), label='节点')
    main_function = forms.CharField(max_length=48, label='主函数')
    args = forms.CharField(max_length=48, label='运行参数')
    note = forms.CharField(max_length=255, required=False, label='说明', widget=forms.Textarea)


class StormAppUpdateForm(StormAppForm):
    user = forms.ModelMultipleChoiceField(
        required=True, label='开发者', queryset=User.objects.filter(profile__role__alias='developer').all()
    )

class StormAppJarForm(ModelForm):
    class Meta:
        model = StormAppJar
        exclude = ['create_time', 'package', 'state', 'md5']
        widgets = {
            'storm_app': HiddenInput(),
            'user': HiddenInput(),
            'active': HiddenInput(),
        }

    def clean_url(self):
        url = self.cleaned_data['url']
        base, ext = os.path.splitext(url)
        if ext != '.jar':
            raise forms.ValidationError('地址有误！请提供jar包地址')
        return url

    def save(self, commit=True):
        instance = super(StormAppJarForm, self).save(commit=commit)
        if 'url' in self.changed_data:
            download_storm_jar.delay(instance.url, instance.id)
        return instance

class StormNodeJarDirForm(ModelForm):
    class Meta:
        model = StormNodeJarDir
        fields = ['storm_node', 'jar_dir', 'note']
        widgets = {
            'storm_node': HiddenInput(),
        }
        labels = {
            'jar_dir': 'Jar包目录(填写绝对路径)'
        }

    def clean_war_dir(self):
        jar_dir = self.cleaned_data['jar_dir']
        ts = self.cleaned_data['storm_node']
        storm_dir = os.path.sep.join(ts.cmd.split(os.path.sep)[:3])
        if storm_dir != os.path.sep.join(jar_dir.split(os.path.sep)[:3]):
            raise forms.ValidationError('请设置在此Storm下的目录!')
        node = NodeProxy(ts.host.ip, settings.NODE_PORT)
        try:
            if not node.path_exists(jar_dir):
                if not node.makedirs(jar_dir):
                    raise forms.ValidationError('在Storm下创建目录失败, marmot可能缺少权限!')
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            raise forms.ValidationError('连接不上此Storm的服务器, 无法验证和创建目录!')
        return jar_dir
