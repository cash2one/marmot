# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import redis

from django.contrib.auth.models import User
from django.contrib.auth.decorators import permission_required, login_required
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse_lazy
from django.views.generic import FormView, ListView, DetailView, DeleteView
from django.http import JsonResponse
from django.shortcuts import render
from django.db import transaction
from django.conf import settings

from utils.mixins import LoginRequiredMixin
from services.models import IceService
from .models import Task, TaskFirewall
from .forms import TaskFirewallForm, TaskIceServiceForm


RDS = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)


class TaskFirewallCreate(LoginRequiredMixin, FormView):
    form_class = TaskFirewallForm
    template_name = 'task/task_firewall_create.html'
    success_url = reverse_lazy('task_list')

    @transaction.atomic
    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        extra_obj = TaskFirewall.objects.create(src_addr=cleaned_data['src_addr'], dest_addr=cleaned_data['dest_addr'],
                                                ports=cleaned_data['ports'])
        Task.objects.create(name=cleaned_data['name'], applicant=self.request.user, type='firewall',
                            extra_id=extra_obj.id, note=cleaned_data['note'])
        return super(TaskFirewallCreate, self).form_valid(form)


class TaskIceServiceCreate(LoginRequiredMixin, FormView):
    form_class = TaskIceServiceForm
    template_name = 'task/task_ice_service_create.html'
    success_url = reverse_lazy('task_list')

    def get_form(self, form_class=None):
        form = super(TaskIceServiceCreate, self).get_form(form_class=form_class)
        ice_service = form.fields['ice_service']
        form.fields['ice_service'].queryset = ice_service.queryset.filter(user=self.request.user).all()
        return form

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        Task.objects.create(name=cleaned_data['name'], applicant=self.request.user, type='ice', deploy=False,
                            extra_id=cleaned_data['ice_service'].id, note=cleaned_data['note'])
        return super(TaskIceServiceCreate, self).form_valid(form)


class TaskList(LoginRequiredMixin, ListView):
    model = Task
    context_object_name = 'tasks'
    template_name = 'task/task_list.html'

    def get_queryset(self):
        queryset = super(TaskList, self).get_queryset()
        user = self.request.user
        if user.profile.role.alias == 'developer':
            queryset = queryset.filter(applicant=user)
        elif user.profile.role.alias == 'CPIS' and user.profile.privilege < 3:
            queryset = queryset.filter(operator=user)
        return queryset.order_by('-create_time')

    def get_context_data(self, **kwargs):
        context = super(TaskList, self).get_context_data(**kwargs)
        context['has_perm_add_task'] = self.request.user.has_perm('task.add_task')
        context['task_type'] = Task.TASK_CHOICE
        return context


class TaskDetail(LoginRequiredMixin, DetailView):
    model = Task
    context_object_name = 'task'
    template_name = 'task/task_detail.html'

    def get_context_data(self, **kwargs):
        context = super(TaskDetail, self).get_context_data(**kwargs)
        context['cpis_list'] = User.objects.filter(profile__role__alias='CPIS').all()
        context['has_perm_assign'] = self.request.user.has_perm('task.assign_task')
        context['has_perm_delete'] = self.request.user.has_perm('task.delete_task')
        context['has_perm_implement'] = self.request.user.has_perm('task.implement_task')
        type_ = self.object.type
        if type_ == 'ice':
            context['ice_service'] = IceService.objects.get(id=self.object.extra_id)
        elif type_ == 'firewall':
            context['firewall'] = TaskFirewall.objects.get(id=self.object.extra_id)
        return context


class TaskDelete(LoginRequiredMixin, DeleteView):
    model = Task
    context_object_name = 'task'
    template_name = 'task/task_confirm_delete.html'
    success_url = reverse_lazy('task_list')

    @method_decorator(permission_required('task.delete_task', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super(TaskDelete, self).dispatch(request, *args, **kwargs)


@login_required
def assign_operator(request, task_id):
    if not request.user.has_perm('task.assign_task'):
        return JsonResponse({'msg': '403-缺少权限'})
    user_id = request.GET.get('cpis', 0)
    try:
        user = User.objects.get(id=user_id)
    except (User.DoesNotExist, ValueError):
        return JsonResponse({'msg': 'user: %s does not exist' % user_id})
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return JsonResponse({'msg': 'task: %s does not exist' % task_id})
    task.operator = user
    task.progress = 20  # 已分配
    task.save()
    return JsonResponse({'msg': 0})


@login_required
def set_task_progress(request, task_id, progress):
    progress = int(progress)
    if not progress or progress not in (10, 20, 30, 40):
        return JsonResponse({'msg': 'progress error - %s' % progress})
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return JsonResponse({'msg': 'task: %s does not exist' % task_id})

    task.progress = progress
    if progress in (30, 40):  # 已完成
        task.done = True
    task.save()
    return JsonResponse({'msg': 0})


@login_required
def task_implement(request, task_id):
    if not request.user.has_perm('task.implement_task'):
        return JsonResponse({'msg': '403-缺少权限'})
    try:
        task = Task.objects.get(id=task_id)
    except User.DoesNotExist:
        return JsonResponse({'msg': 'task: %s does not exist' % task_id})
    try:
        task.implement()
    except Exception as e:
        return JsonResponse({'msg': 'unknown error: %s' % e})
    return JsonResponse({'msg': 0})


@login_required
def node_task_log_view(request, identifier):
    return render(request, 'task/node_task_log_view.html', {'identifier': identifier})


def task_implement_log(request, identifier):
    ret = [RDS.lpop(identifier) for i in xrange(RDS.llen(identifier))]
    return JsonResponse({'msg': ret})
