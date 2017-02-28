# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm


class LoginForm(AuthenticationForm):

    error_messages = {
        'invalid_login': "请输入正确的用户名和密码!",
        'inactive': "这个账号被禁用了!",
    }

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.initial = self.initial or {'username': '', 'password': ''}


class ChangePasswordForm(PasswordChangeForm):

    error_messages = {
        'password_incorrect': "原密码不正确!",
        'password_mismatch': "两次输入密码不一致!",
    }

    def __init__(self, *args, **kwargs):
        super(ChangePasswordForm, self).__init__(*args, **kwargs)
        self.initial = self.initial or {'old_password': '',
                                        'new_password1': '',
                                        'new_password2': ''}
