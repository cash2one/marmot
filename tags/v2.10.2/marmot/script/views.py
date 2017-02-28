# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import redis

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, ListView, UpdateView, DetailView, DeleteView
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.conf import settings

from utils.mixins import LoginRequiredMixin, PermissionRequiredMixin

from .models import Script
from .forms import ScriptForm


RDS = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)


class ScriptCreate(PermissionRequiredMixin, CreateView):
    model = Script
    form_class = ScriptForm
    template_name = 'script/script_form.html'
    success_url = reverse_lazy('script_list')
    permission_required = 'script.add_script'

    def get_initial(self):
        initial = super(ScriptCreate, self).get_initial()
        initial['owner'] = self.request.user
        return initial


class ScriptUpdate(PermissionRequiredMixin, UpdateView):
    model = Script
    form_class = ScriptForm
    context_object_name = 'script'
    template_name = 'script/script_form.html'
    permission_required = 'script.change_script'


class ScriptDetail(LoginRequiredMixin, DetailView):
    model = Script
    context_object_name = 'script'
    template_name = 'script/script_detail.html'


class ScriptDelete(PermissionRequiredMixin, DeleteView):
    model = Script
    context_object_name = 'script'
    template_name = 'script/script_confirm_delete.html'
    success_url = reverse_lazy('script_list')
    permission_required = 'script.delete_script'


class ScriptList(LoginRequiredMixin, ListView):
    model = Script
    paginate_by = 20
    context_object_name = 'script_list'
    template_name = 'script/scripts.html'

    def get_queryset(self):
        queryset = super(ScriptList, self).get_queryset()
        user = self.request.user
        if user.profile.role.alias == 'developer' and user.profile.privilege < 3:
            queryset = queryset.filter(owner=user)
        return queryset.order_by('-create_time')


@login_required
def run_script(request, pk):
    if not request.user.has_perm('script.run_script'):
        return JsonResponse({'msg': '403 - 缺少权限'})
    try:
        script = Script.objects.get(id=pk)
    except Script.DoesNotExist:
        return JsonResponse({'msg': 'script: %s does not exist' % pk})
    if not script.server.is_alive:
        return JsonResponse({'msg': '目标主机不在线'})
    try:
        script.push_task()
    except Exception as e:
        return JsonResponse({'msg': unicode(e)})
    return JsonResponse({'msg': 0})


@login_required
def script_implement_log_view(request, script_id):
    try:
        script = Script.objects.get(id=script_id)
    except Script.DoesNotExist:
        return HttpResponseRedirect(reverse('script_list'))
    return render(request, 'script/script_implement_log_view.html', {'script': script})


def script_implement_log(request, identifier):
    return JsonResponse({'msg': [RDS.lpop(identifier) for _ in xrange(RDS.llen(identifier))]})
