# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from utils import serialize_form_errors
from utils.mixins import LoginRequiredMixin
from .forms import LoginForm, ChangePasswordForm


class LoginView(TemplateView):
    template_name = 'accounts/login.html'

    def get(self, request, *args, **kwargs):
        context = super(LoginView, self).get_context_data(**kwargs)
        context['form'] = LoginForm()
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)  # 认证
            if user is not None and user.is_active:
                login(request, user)
                return redirect('/')
            else:
                error_msg = '用户名或密码错误！'
        else:
            error_msg = serialize_form_errors(form)
        messages.info(request, error_msg)
        context = super(LoginView, self).get_context_data(**kwargs)
        context['form'] = form
        return self.render_to_response(context)


@login_required
def logout_view(request):
    if request.user.is_authenticated():
        logout(request)
    return redirect('/accounts/login/')


@login_required
def profile_view(request, username):
    return render(request, 'accounts/profile.html')


@login_required
def change_pwd_done(request):
    return render(request, 'accounts/change_pwd_done.html')


class ChangePasswordView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/change_pwd.html'

    def get(self, request, *args, **kwargs):
        context = super(ChangePasswordView, self).get_context_data(**kwargs)
        context['form'] = ChangePasswordForm()
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        user = request.user
        form = ChangePasswordForm(request.POST, user=user)

        if form.is_valid():
            password_new = form.cleaned_data['password_new']
            user.set_password(password_new)
            user.save()
            update_session_auth_hash(request, user)  # 修改密码不使session失效
            return redirect('/accounts/changepwddone/')
        else:
            error_msg = serialize_form_errors(form)
            messages.info(request, error_msg)
            context = super(ChangePasswordView, self).get_context_data(**kwargs)
            context['form'] = form
            return self.render_to_response(context)
