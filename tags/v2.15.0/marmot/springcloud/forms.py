# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import re
import hashlib

from django import forms
from django.forms import ModelForm
from django.forms.widgets import Textarea, HiddenInput

from .models import SpringCloudCluster, SpringCloudNode, SpringCloudApp, SpringCloudFile


class SpringCloudClusterForm(ModelForm):
    class Meta:
        model = SpringCloudCluster
        exclude = ['create_time']
        widgets = {
            'created_by': HiddenInput(),
            'note': Textarea(attrs={'rows': 5}),
        }


class SpringCloudNodeForm(ModelForm):
    class Meta:
        model = SpringCloudNode
        exclude = ['create_time']
        widgets = {
            'cluster': HiddenInput(),
            'created_by': HiddenInput(),
            'note': Textarea(attrs={'rows': 5}),
        }


class SpringCloudAppForm(ModelForm):
    nodes = forms.ModelMultipleChoiceField(queryset=SpringCloudNode.objects.all(), label='节点',
                                           widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = SpringCloudApp
        exclude = ['create_time']
        widgets = {
            'cluster': HiddenInput(),
            'created_by': HiddenInput(),
            'note': Textarea(attrs={'rows': 5}),
        }
        labels = {
            'name': '名称(注意: 一定要和微服务app目录中的项目文件夹名一致)',
            'startup': '启动脚本路径(绝对路径)',
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise forms.ValidationError('只能输入字母、数字、下划线和中横线')
        return name

    def clean_script(self):
        if self.cleaned_data['script']:
            script = str(self.cleaned_data['script'])
            if script[-3:] != '.sh':
                raise forms.ValidationError('文件格式错误, 请上传.sh文件!')
        return self.cleaned_data['script']


class SpringCloudFileForm(ModelForm):
    class Meta:
        model = SpringCloudFile
        exclude = ['create_time', 'md5']
        widgets = {
            'app': HiddenInput(),
            'created_by': HiddenInput(),
        }

    def save(self, commit=True):
        filename = self.cleaned_data['file'].name
        app_name = self.cleaned_data['app'].name
        cluster_name = self.cleaned_data['app'].cluster.name
        _type = self.cleaned_data['type']

        if _type == 0:
            real_fn = 'springcloud/{0}/{1}/lib/{2}'.format(cluster_name, app_name, filename)
        elif _type == 1:
            real_fn = 'springcloud/{0}/{1}/lib/libs/{2}'.format(cluster_name, app_name, filename)
        elif _type == 2:
            real_fn = 'springcloud/{0}/{1}/config/{2}'.format(cluster_name, app_name, filename)
        else:
            raise ValueError('SpringCloudFile - type: %s ERROR!' % _type)

        SpringCloudFile.objects.filter(file=real_fn).delete()

        instance = super(SpringCloudFileForm, self).save(commit=commit)
        if instance.file:
            if os.path.isfile(instance.file.path):
                instance.md5 = hashlib.md5(open(instance.file.path, 'rb').read()).hexdigest()
                instance.save()
        return instance
