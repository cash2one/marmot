# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms


class LoginForm(forms.Form):
    username = forms.CharField(max_length=24)
    password = forms.CharField(max_length=24)

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.initial = self.initial or {'username': '', 'password': ''}


class ChangePasswordForm(forms.Form):
    password_current = forms.CharField(max_length=24)
    password_new = forms.CharField(max_length=24)
    password_new_confirm = forms.CharField(max_length=24)

    def __init__(self, *args, **kwargs):
        if 'user' in kwargs:
            self.user = kwargs.pop('user')
        super(ChangePasswordForm, self).__init__(*args, **kwargs)
        self.initial = self.initial or {'password_current': '', 'password_new': '', 'password_new_confirm': ''}

    def clean_password_current(self):
        if not self.user.check_password(self.cleaned_data.get('password_current')):
            raise forms.ValidationError(u'原始密码错误')
        return self.cleaned_data['password_current']

    def clean_password_new_confirm(self):
        if 'password_new' in self.cleaned_data and 'password_new_confirm' in self.cleaned_data:
            if self.cleaned_data['password_new'] != self.cleaned_data['password_new_confirm']:
                raise forms.ValidationError(u'两次新密码不一致！')
        return self.cleaned_data['password_new_confirm']


class ProfileForm(forms.Form):
    cell = forms.CharField(max_length=32)
    mail = forms.EmailField(max_length=48)

    def clean_cell(self):
        cell = self.cleaned_data['cell']
        if len(cell) != 11 or not cell.isdigit():
            raise forms.ValidationError('手机号格式错误')
        return self.cleaned_data['cell']

    def clean_mail(self):
        mail = self.cleaned_data['mail']
        if mail[mail.find('@')+1:] != '100credit.com':
            raise forms.ValidationError('只能使用百融内部邮箱')
        return self.cleaned_data['mail']
