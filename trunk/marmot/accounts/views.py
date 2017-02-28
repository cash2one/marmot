# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse

from utils.mixins import LoginRequiredMixin

from .forms import LoginForm, ChangePasswordForm


class LoginView(TemplateView):
    template_name = 'accounts/login.html'

    def get(self, request, *args, **kwargs):
        ticket = request.GET.get('ticket')
        if ticket:
            user = authenticate(ticket=ticket)
            if user and user.is_active:
                login(request, user)
                next_page = request.GET.get('next')
                if next_page:
                    response = redirect(next_page)
                else:
                    response = redirect('/')
                # 在cookie中设置fromCas等于yes, 标记用户是从cas登录的
                response.set_cookie('fromCas', 'yes')
                return response
            else:
                return HttpResponse('拒绝登录')
        else:
            context = super(LoginView, self).get_context_data(**kwargs)
            context['form'] = LoginForm()
            return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_page = request.GET.get('next')
            if next_page:
                response = redirect(next_page)
            else:
                response = redirect('/')
        else:
            messages.info(request, form.non_field_errors().as_text())
            context = super(LoginView, self).get_context_data(**kwargs)
            context['form'] = form
            response = self.render_to_response(context)
        response.set_cookie('fromCas', 'no')
        return response


@login_required
def logout_view(request):
    if request.user.is_authenticated():
        logout(request)
    if request.COOKIES.get('fromCas') == 'yes':
        return redirect(settings.CAS_MAIN_URL)
    else:
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
        context['form'] = ChangePasswordForm(request.user)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        user = request.user
        form = ChangePasswordForm(user, data=request.POST)

        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)  # 修改密码不使session失效
            return redirect('/accounts/changepwddone/')
        else:
            error = form.errors.as_data().values()[0][0].messages[-1]
            messages.info(request, error)
            context = super(ChangePasswordView, self).get_context_data(**kwargs)
            context['form'] = form
            return self.render_to_response(context)
