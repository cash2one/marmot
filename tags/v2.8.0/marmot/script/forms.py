# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.forms import ModelForm
from django.forms.widgets import Textarea, HiddenInput

from .models import Script


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
