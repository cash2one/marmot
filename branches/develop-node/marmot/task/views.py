# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import urlparse
import logging

from django.conf import settings
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth.decorators import permission_required, login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, DeleteView, CreateView, UpdateView
from django.http import JsonResponse, HttpResponseRedirect, HttpResponseNotFound
from django.utils.http import urlencode

import celerymail

from utils.mixins import LoginRequiredMixin, JSONResponseMixin, PermissionRequiredMixin
from workflow.models import WorkflowModelRelation, Transition
from workflow.exceptions import WorkflowException

from .models import (
    Task, TaskFirewall, FirewallGoal,
    TaskDNS, TaskIce, TaskTomcat, TaskSpringCloud
)
from .forms import (
    TaskIceForm, TaskTomcatForm,
    TaskDNSForm, TaskSpringCloudForm
)


logger = logging.getLogger('marmot')


class TaskFirewallCreate(PermissionRequiredMixin, TemplateView):
    template_name = 'task/task_firewall_create.html'
    success_url = reverse_lazy('task_list')
    permission_required = 'task.add_task'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(TaskFirewallCreate, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not request.is_ajax():
            return HttpResponseNotFound

        data = json.loads(request.body)

        task_firewall = TaskFirewall(name=data['taskName'], note=data['taskNote'])
        task_firewall.save()
        firewall_goals = []
        for d in data['goals']:
            firewall_goals.append(
                FirewallGoal(
                    src_addr=d['srcAddr'], dest_addr=d['destAddr'],
                    ports=d['ports'], task_firewall=task_firewall
                )
            )
        FirewallGoal.objects.bulk_create(firewall_goals)

        try:
            Task.create(task_firewall, request.user)
        except WorkflowException as e:
            return JsonResponse({'msg': str(e)})

        return JsonResponse({'msg': 0})


class TaskDNSCreate(PermissionRequiredMixin, CreateView):
    model = TaskDNS
    form_class = TaskDNSForm
    template_name = 'task/task_dns_form.html'
    success_url = reverse_lazy('task_list')
    permission_required = 'task.add_task'

    def form_valid(self, form):
        resp = super(TaskDNSCreate, self).form_valid(form)
        Task.create(self.object, self.request.user)
        return resp


class TaskIceAppCreate(TaskDNSCreate):
    model = TaskIce
    form_class = TaskIceForm
    template_name = 'task/task_ice_app_form.html'
    success_url = reverse_lazy('task_list')
    permission_required = 'task.add_task'

    def get_form(self, form_class=None):
        form = super(TaskIceAppCreate, self).get_form(form_class=form_class)
        ice_apps = form.fields['ice_app']
        form.fields['ice_app'].queryset = ice_apps.queryset.filter(users=self.request.user).all()
        return form


class TaskIceAppUpdate(PermissionRequiredMixin, UpdateView):
    model = TaskIce
    form_class = TaskIceForm
    template_name = 'task/task_ice_app_form.html'
    permission_required = 'task.change_task'

    def get_success_url(self):
        return self.object.tasks.first().get_absolute_url()

    def get_form(self, form_class=None):
        form = super(TaskIceAppUpdate, self).get_form(form_class=form_class)
        ice_apps = form.fields['ice_app']
        form.fields['ice_app'].queryset = ice_apps.queryset.filter(users=self.request.user).all()
        return form


class TaskTomcatAppCreate(TaskDNSCreate):
    model = TaskTomcat
    form_class = TaskTomcatForm
    template_name = 'task/task_tomcat_app_form.html'
    success_url = reverse_lazy('task_list')
    permission_required = 'task.add_task'

    def get_form(self, form_class=None):
        form = super(TaskTomcatAppCreate, self).get_form(form_class=form_class)
        tomcat_apps = form.fields['tomcat_app']
        form.fields['tomcat_app'].queryset = tomcat_apps.queryset.filter(users=self.request.user).all()
        return form


class TaskTomcatAppUpdate(PermissionRequiredMixin, UpdateView):
    model = TaskTomcat
    form_class = TaskTomcatForm
    template_name = 'task/task_tomcat_app_form.html'
    permission_required = 'task.change_task'

    def get_success_url(self):
        return self.object.tasks.first().get_absolute_url()

    def get_form(self, form_class=None):
        form = super(TaskTomcatAppUpdate, self).get_form(form_class=form_class)
        tomcat_apps = form.fields['tomcat_app']
        form.fields['tomcat_app'].queryset = tomcat_apps.queryset.filter(users=self.request.user).all()
        return form


class TaskSpringCloudAppCreate(TaskDNSCreate):
    model = TaskSpringCloud
    form_class = TaskSpringCloudForm
    template_name = 'task/task_springcloud_app_form.html'
    success_url = reverse_lazy('task_list')
    permission_required = 'task.add_task'

    def get_form(self, form_class=None):
        form = super(TaskSpringCloudAppCreate, self).get_form(form_class=form_class)
        apps = form.fields['app']
        form.fields['app'].queryset = apps.queryset.filter(develops=self.request.user).all()
        return form


class TaskSpringCloudAppUpdate(PermissionRequiredMixin, UpdateView):
    model = TaskSpringCloud
    form_class = TaskSpringCloudForm
    template_name = 'task/task_springcloud_app_form.html'
    permission_required = 'task.change_task'

    def get_success_url(self):
        return self.object.tasks.first().get_absolute_url()

    def get_form(self, form_class=None):
        form = super(TaskSpringCloudAppUpdate, self).get_form(form_class=form_class)
        apps = form.fields['app']
        form.fields['app'].queryset = apps.queryset.filter(develops=self.request.user).all()
        return form


class TaskList(LoginRequiredMixin, ListView):
    model = Task
    paginate_by = 20
    context_object_name = 'tasks'
    template_name = 'task/task_list.html'

    def get_queryset(self):
        queryset = super(TaskList, self).get_queryset()
        user = self.request.user
        self.show = self.request.GET.get获取('show', 'self').lower()  # self: 我的任务; all: 所有任务
        if self.show != 'all':
            queryset = queryset.filter(
                    Q(workflowactivity__participants__user=user) |
                    Q(workflowactivity__current_state__users=user) |
                    Q(workflowactivity__current_state__groups__in=user.groups.all())
                )
        return queryset.select_related('workflowactivity', 'workflowactivity__current_state').distinct().all()

    def get_context_data(self, **kwargs):
        context = super(TaskList, self).get_context_data(**kwargs)
        context['show'] = self.show
        context['task_type_list'] = [(m.label, m.label_raw) for m in
                                     [wmr.content_type.model_class() for wmr in WorkflowModelRelation.objects.all()]]
        # 用于分页器的参数
        context['extra_url_param'] = urlencode({'show': self.show})
        return context


class TaskDetail(LoginRequiredMixin, DetailView):
    model = Task
    context_object_name = 'task'
    template_name = 'task/task_detail.html'

    def get_context_data(self, **kwargs):
        context = super(TaskDetail, self).get_context_data(**kwargs)
        # 测试人员列表
        context['te_list'] = User.objects.filter(profile__role__alias='TE').exclude(profile__test=True).all()
        # 当前状态支持的传输
        context['transitions'] = self.object.has_perm_use_transitions(self.request.user)
        # 是否有权限更新任务信息
        context['is_updatable'] = self.object.has_perm_update(self.request.user)
        return context


class TaskDelete(LoginRequiredMixin, DeleteView):
    model = Task
    context_object_name = 'task'
    template_name = 'task/task_confirm_delete.html'
    success_url = reverse_lazy('task_list')

    @method_decorator(permission_required('task.delete_task', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super(TaskDelete, self).dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.content_object.delete()
        self.object.delete()
        return HttpResponseRedirect(success_url)


@login_required
def progress_transition(request, task_id):
    """
    执行一个transition
    """
    transaction_id = request.GET.get('transId')
    if transaction_id is None:
        return JsonResponse({'msg': 'Transition <%s> does not exist' % transaction_id})
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return JsonResponse({'msg': 'Task <%s> does not exist' % task_id})

    try:
        transaction = Transition.objects.get(id=transaction_id)
    except Transition.DoesNotExist:
        return JsonResponse({'msg': 'Transition <%s> does not exist' % transaction_id})

    try:
        task.workflowactivity.progress(transaction, request.user)
    except WorkflowException as e:
        return JsonResponse({'msg': str(e)})

    return JsonResponse({'msg': 0})


@login_required
@csrf_exempt
def add_comment(request, task_id):
    try:
        data = json.loads(request.body)
    except ValueError as e:
        return JsonResponse({'msg': str(e)})

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return JsonResponse({'msg': 'Task <%s> Does not exist' % task_id})

    note = data.get('note', '')

    if note.strip():
        try:
            task.workflowactivity.add_comment(request.user, note)
        except WorkflowException as e:
            return JsonResponse({'msg': str(e)})

    task.workflowactivity.add_participant(request.user)
    return JsonResponse({'msg': 0})


@login_required
def assign_te(request, task_id):
    """
    给任务分配测试人员
    """
    if not request.user.has_perm('task.assign_te'):
        return JsonResponse({'msg': '403-缺少权限'})

    te_user_id = request.GET.get('te')  # 测试人员id
    if te_user_id is None:
        return JsonResponse({'msg': 'url中缺少te参数'})

    try:
        te_user = User.objects.get(id=te_user_id)
    except User.DoesNotExist:
        return JsonResponse({'msg': 'User <%s> does not exist' % te_user_id})

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return JsonResponse({'msg': 'Task <%s> does not exist' % task_id})

    transitions = task.get_current_transitions()
    if transitions:
        # 有可用transions时, 才执行后续的分配测试操作
        # 如果已经没有可用传输, 表示task已经结束, 没有分配测试的必要了
        tran = transitions.filter(label="assignTe").first()
        if tran:
            task.workflowactivity.progress(tran, request.user, note='分配测试人员: %s' % te_user.get_full_name())
        else:
            task.workflowactivity.add_comment(request.user, note='分配测试人员: %s' % te_user.get_full_name())

        if task.workflowactivity.add_participant(te_user):
            # 如果指派的人已经是参与者就不发邮件了
            message = '<h3>{title}</h3>' \
                      '<a href="{link}">任务名称： {name}</a>' \
                      '<p>任务类型： {type}</p>'\
                      '<p>申请人： {applicant}</p>'\
                .format(title='Marmot -- 有个任务指派给你',
                        name=task.name, type=task.type_raw, applicant=task.applicant.get_full_name(),
                        link=urlparse.urljoin(settings.MAIN_DOMAIN, task.get_absolute_url()))

            celerymail.send_html_mail('Marmot - 任务提醒', message, [te_user.email])

    return JsonResponse({'msg': 0})
