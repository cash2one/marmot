# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import os
import hashlib

from django.forms import forms, ModelForm
from django.forms.widgets import Textarea, HiddenInput

from .models import NodeApp, NodeSrcPkg


class NodeAppCreateForm(ModelForm):
    class Meta:
        model = NodeApp
        exclude = ['create_time', 'pid']
        widgets = {
            'created_by': HiddenInput(),
            'note': Textarea(attrs={'rows': 5}),
        }
        labels = {
            'name': '名称(英文名)',
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            raise forms.ValidationError('只能输入字母、数字和下划线')
        return name

    def clean_pid(self):
        pid = self.cleaned_data['pid']
        if pid:
            if not re.match(r'^[0-9]+$', pid):
                raise forms.ValidationError('pid只能是数字')
        return pid


class NodeAppEditForm(NodeAppCreateForm):
    class Meta:
        model = NodeApp
        exclude = ['create_time']
        widgets = {
            'created_by': HiddenInput(),
            'note': Textarea(attrs={'rows': 5}),
        }
        labels = {
            'name': '名称(英文名)',
        }


class NodeSrcPkgForm(ModelForm):
    class Meta:
        model = NodeSrcPkg
        exclude = ['create_time', 'active', 'md5']
        widgets = {
            'app': HiddenInput(),
            'created_by': HiddenInput(),
            'note': Textarea(attrs={'rows': 5}),
        }

    def clean_package(self):
        pkg = str(self.cleaned_data['package'])
        if pkg[-4:] != '.zip':
            raise forms.ValidationError('请上传zip文件!')
        return self.cleaned_data['package']

    def save(self, commit=True):
        instance = super(NodeSrcPkgForm, self).save(commit=commit)
        if instance.package:
            if os.path.isfile(instance.package.path):
                instance.md5 = hashlib.md5(open(instance.package.path, 'rb').read()).hexdigest()
                instance.save()
        return instance
