# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import redis

from django.db import transaction
from django.contrib.auth.models import User
from django.contrib.auth.decorators import permission_required, login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse_lazy
from django.views.generic import TemplateView, FormView, ListView, DetailView, DeleteView
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.conf import settings

from utils.mixins import LoginRequiredMixin, JSONResponseMixin
from .models import Task, TaskFirewall, FirewallGoal
from .forms import TaskIceServiceForm, TaskTomcatAppForm


RDS = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)


class TaskFirewallCreate(LoginRequiredMixin, TemplateView):
    template_name = 'task/task_firewall_create.html'
    success_url = reverse_lazy('task_list')

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(TaskFirewallCreate, self).dispatch(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        if not request.is_ajax():
            raise Http404
        data = json.loads(request.body)
        task_firewall = TaskFirewall.objects.create()
        firewall_goals = []
        for d in data['goals']:
            firewall_goals.append(
                FirewallGoal(
                    src_addr=d['srcAddr'], dest_addr=d['destAddr'],
                    ports=d['ports'], task_firewall=task_firewall
                )
            )
        FirewallGoal.objects.bulk_create(firewall_goals)
        task = Task.objects.create(name=data['taskName'], applicant=request.user,
                                   note=data['taskNote'], content_object=task_firewall)
        task.submit()
        return JsonResponse({'msg': 0})


class TaskIceServiceCreate(LoginRequiredMixin, FormView):
    form_class = TaskIceServiceForm
    template_name = 'task/task_ice_service_create.html'
    success_url = reverse_lazy('task_list')

    def get_form(self, form_class=None):
        form = super(TaskIceServiceCreate, self).get_form(form_class=form_class)
        ice_service = form.fields['ice_service']
        form.fields['ice_service'].queryset = ice_service.queryset.filter(users=self.request.user).all()
        return form

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        task = Task.objects.create(name=cleaned_data['name'], applicant=self.request.user, deploy=True,
                                   content_object=cleaned_data['ice_service'], note=cleaned_data['note'])
        task.submit()
        return super(TaskIceServiceCreate, self).form_valid(form)


class TaskTomcatAppCreate(LoginRequiredMixin, FormView):
    form_class = TaskTomcatAppForm
    template_name = 'task/task_tomcat_app_create.html'
    success_url = reverse_lazy('task_list')

    def get_form(self, form_class=None):
        form = super(TaskTomcatAppCreate, self).get_form(form_class=form_class)
        tomcat_apps = form.fields['tomcat_app']
        form.fields['tomcat_app'].queryset = tomcat_apps.queryset.filter(users=self.request.user).all()
        return form

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        task = Task.objects.create(name=cleaned_data['name'], applicant=self.request.user, deploy=True,
                                   content_object=cleaned_data['tomcat_app'], note=cleaned_data['note'])
        task.submit()
        return super(TaskTomcatAppCreate, self).form_valid(form)


class TaskList(LoginRequiredMixin, ListView):
    model = Task
    paginate_by = 20
    context_object_name = 'tasks'
    template_name = 'task/task_list.html'

    def get_queryset(self):
        queryset = super(TaskList, self).get_queryset()
        user = self.request.user
        if user.profile.role.alias == 'developer' and user.profile.privilege < 3:
            queryset = queryset.filter(applicant=user)
        elif user.profile.role.alias == 'CPIS' and user.profile.privilege < 3:
            queryset = queryset.filter(operator=user)
        return queryset.order_by('-create_time')

    def get_context_data(self, **kwargs):
        context = super(TaskList, self).get_context_data(**kwargs)
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
            context['ice_service'] = self.object.content_object
        elif type_ == 'firewall':
            context['firewall'] = self.object.content_object
        elif type_ == 'tomcat':
            context['tomcat_app'] = self.object.content_object
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
    task.assign(user)
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
    if progress == 30:
        task.ignore()
    elif progress == 40:
        task.over()
    task.save()
    return JsonResponse({'msg': 0})


@login_required
def node_task_log_view(request, identifier):
    return render(request, 'task/node_task_log_view.html', {'identifier': identifier})


@login_required
def task_implement_log(request, identifier):
    return JsonResponse({'msg': [RDS.lpop(identifier) for _ in range(RDS.llen(identifier))]})
