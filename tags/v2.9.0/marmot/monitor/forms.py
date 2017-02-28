# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import xmlrpclib
import httplib

from django import forms
from django.forms import ModelForm
from django.forms.widgets import HiddenInput, CheckboxInput
from django.conf import settings

from utils.node_proxy import NodeProxy

from .models import (
    RedisClusterMonitor, RedisNode, ESMonitor, HBaseClusterMonitor, Neo4jMonitor
)


class RedisClusterMonitorForm(ModelForm):
    class Meta:
        model = RedisClusterMonitor
        exclude = ['create_time']
        widgets = {
            'active': CheckboxInput(),
            'created_by': HiddenInput(),
        }


class RedisNodeForm(ModelForm):
    class Meta:
        model = RedisNode
        exclude = ['create_time']
        widgets = {
            'cluster': HiddenInput(),
            'created_by': HiddenInput(),
        }


class HBaseClusterMonitorForm(ModelForm):
    class Meta:
        model = HBaseClusterMonitor
        exclude = ['create_time']
        widgets = {
            'active': CheckboxInput(),
            'created_by': HiddenInput(),
        }

    def clean_host(self):
        node = NodeProxy(self.cleaned_data['host'], settings.NODE_PORT)
        try:
            node.is_alive()
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            raise forms.ValidationError('连不上此主机!')
        return self.cleaned_data['host']


class ESMonitorForm(ModelForm):
    class Meta:
        model = ESMonitor
        fields = ['name', 'host', 'addr', 'active', 'note', 'created_by']
        widgets = {
            'active': CheckboxInput(),
            'created_by': HiddenInput(),
        }

    def clean_host(self):
        node = NodeProxy(self.cleaned_data['host'], settings.NODE_PORT)
        try:
            node.is_alive()
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            raise forms.ValidationError('连不上此主机!')
        return self.cleaned_data['host']

    def clean_addr(self):
        node = NodeProxy(self.cleaned_data['host'], settings.NODE_PORT)
        try:
            node.get_es_info(self.cleaned_data['addr'])
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            raise forms.ValidationError('地址不通!')
        return self.cleaned_data['addr']


class Neo4jMonitorForm(ModelForm):
    class Meta:
        model = Neo4jMonitor
        exclude = ['create_time']
        widgets = {
            'active': CheckboxInput(),
            'created_by': HiddenInput(),
        }

    def clean_host(self):
        node = NodeProxy(self.cleaned_data['host'], settings.NODE_PORT)
        try:
            node.is_alive()
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            raise forms.ValidationError('连不上此主机!')
        return self.cleaned_data['host']
