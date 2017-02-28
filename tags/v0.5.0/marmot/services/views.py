# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

import redis

from django.core.urlresolvers import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import CreateView, ListView, UpdateView, DetailView, DeleteView
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.conf import settings

from utils.mixins import LoginRequiredMixin, PermissionRequiredMixin

from .models import IceServiceCenter, IceServiceNode, IceService, Script
from .forms import IceServiceCenterForm, IceServiceNodeForm, IceServiceForm, ScriptForm


RDS = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)

errlog = logging.getLogger('marmot')


class IceServiceCenterCreate(PermissionRequiredMixin, CreateView):
    model = IceServiceCenter
    form_class = IceServiceCenterForm
    template_name = 'services/ice_service_center_form.html'
    success_url = reverse_lazy('ice_service_center_list')
    permission_required = 'services.add_iceservicecenter'
    raise_exception = True


class IceServiceCenterUpdate(PermissionRequiredMixin, UpdateView):
    model = IceServiceCenter
    form_class = IceServiceCenterForm
    context_object_name = 'ice_service_center'
    template_name = 'services/ice_service_center_form.html'
    permission_required = 'services.change_iceservicecenter'
    raise_exception = True


class IceServiceCenterDetail(LoginRequiredMixin, DetailView):
    model = IceServiceCenter
    context_object_name = 'ice_service_center'
    template_name = 'services/ice_service_center_detail.html'

    def get_context_data(self, **kwargs):
        context = super(IceServiceCenterDetail, self).get_context_data(**kwargs)
        user = self.request.user
        ice_services = self.object.iceservice_set.all()
        if user.profile.role.alias == 'developer':
            ice_services = ice_services.filter(user=user)
        context['ice_service_list'] = ice_services
        context['ice_service_node_list'] = self.object.iceservicenode_set.all()
        context['servers_online'] = RDS.keys()
        context['all_registry_info'] = self.object.get_all_registry_info()
        context['all_node_info'] = self.object.get_all_node_info()
        context['all_app_info'] = self.object.get_all_app_info()
        return context


class IceServiceCenterDelete(PermissionRequiredMixin, DeleteView):
    model = IceServiceCenter
    context_object_name = 'ice_service_center'
    template_name = 'services/ice_service_center_confirm_delete.html'
    success_url = reverse_lazy('ice_service_center_list')
    permission_required = 'services.delete_iceservicecenter'
    raise_exception = True


class IceServiceCenterList(LoginRequiredMixin, ListView):
    model = IceServiceCenter
    context_object_name = 'ice_service_center_list'
    template_name = 'services/ice_service_center_list.html'

    def get_context_data(self, **kwargs):
        context = super(IceServiceCenterList, self).get_context_data(**kwargs)
        context['has_perm_add_center'] = self.request.user.has_perm('services.add_iceservicecenter')
        return context


class IceServiceNodeCreate(PermissionRequiredMixin, CreateView):
    model = IceServiceNode
    form_class = IceServiceNodeForm
    template_name = 'services/ice_service_node_form.html'
    success_url = '/services/ice-service-center/%s'
    permission_required = 'services.add_iceservicenode'
    raise_exception = True

    def get_initial(self):
        initial = super(IceServiceNodeCreate, self).get_initial()
        self.center = IceServiceCenter.objects.get(id=self.args[0])
        initial['center'] = self.center
        initial['user'] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super(IceServiceNodeCreate, self).get_context_data(**kwargs)
        context['center'] = self.center
        return context

    def get_success_url(self):
        return self.success_url % self.args[0]


class IceServiceNodeUpdate(PermissionRequiredMixin, UpdateView):
    model = IceServiceNode
    form_class = IceServiceNodeForm
    context_object_name = 'ice_service_node'
    template_name = 'services/ice_service_node_form.html'
    permission_required = 'services.change_iceservicenode'
    raise_exception = True


class IceServiceNodeDetail(LoginRequiredMixin, DetailView):
    model = IceServiceNode
    context_object_name = 'ice_service_node'
    template_name = 'services/ice_service_node_detail.html'


class IceServiceNodeDelete(PermissionRequiredMixin, DeleteView):
    model = IceServiceNode
    context_object_name = 'ice_service_node'
    template_name = 'services/ice_service_node_confirm_delete.html'
    success_url = '/services/ice-service-center/%s'
    permission_required = 'services.delete_iceservicenode'
    raise_exception = True

    def get_success_url(self):
        return self.success_url % self.object.center.id


class IceServiceCreate(PermissionRequiredMixin, CreateView):
    model = IceService
    form_class = IceServiceForm
    template_name = 'services/ice_service_form.html'
    success_url = '/services/ice-service-center/%s'
    permission_required = 'services.add_iceservice'
    raise_exception = True

    def get_initial(self):
        initial = super(IceServiceCreate, self).get_initial()
        self.center = IceServiceCenter.objects.get(id=self.args[0])
        initial['center'] = self.center
        initial['user'] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super(IceServiceCreate, self).get_context_data(**kwargs)
        context['center'] = self.center
        return context

    def get_success_url(self):
        return self.success_url % self.args[0]


class IceServiceUpdate(PermissionRequiredMixin, UpdateView):
    model = IceService
    form_class = IceServiceForm
    context_object_name = 'ice_service'
    template_name = 'services/ice_service_form.html'
    permission_required = 'services.change_iceservice'
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user.profile.role.alias == 'developer' and self.object.user != request.user:
            raise PermissionDenied('this is not your IceService')
        return super(IceServiceUpdate, self).dispatch(request, *args, **kwargs)


class IceServiceDetail(LoginRequiredMixin, DetailView):
    model = IceService
    context_object_name = 'ice_service'
    template_name = 'services/ice_service_detail.html'

    def get_context_data(self, **kwargs):
        context = super(IceServiceDetail, self).get_context_data(**kwargs)
        context['application_nodes'] = self.object.get_application_nodes()
        return context


class IceServiceDelete(PermissionRequiredMixin, DeleteView):
    model = IceService
    context_object_name = 'ice_service'
    template_name = 'services/ice_service_confirm_delete.html'
    success_url = '/services/ice-service-center/%s'
    permission_required = 'services.delete_iceservice'
    raise_exception = True

    def get_success_url(self):
        return self.success_url % self.object.center.id

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user.profile.role.alias == 'developer' and self.object.user != request.user:
            raise PermissionDenied('this is not your IceService')
        return super(IceServiceDelete, self).dispatch(request, *args, **kwargs)


@login_required
def switch_ice_server_node_state(request, service_id, node_id, state):
    if not request.user.has_perm('services.deploy'):
        return JsonResponse({'msg': '你无权操作此项'})
    try:
        service = IceService.objects.get(id=service_id)
    except IceService.DoesNotExist:
        return JsonResponse({'msg': 'service: %s does not exist' % service_id})
    try:
        if int(state):
            service.start_server(node_id)
        else:
            service.stop_server(node_id)
    except Exception as e:
        return JsonResponse({'msg': unicode(e)})
    return JsonResponse({'msg': 0})


@login_required
def push_ice_service_pkg(request, service_id):
    if not request.user.has_perm('services.deploy'):
        return JsonResponse({'msg': '你无权操作此项'})
    try:
        service = IceService.objects.get(id=service_id)
    except IceService.DoesNotExist:
        return JsonResponse({'msg': 'service: %s does not exist' % service_id})
    try:
        service.push_tasks()
    except Exception as e:
        return JsonResponse({'msg': unicode(e)})
    return JsonResponse({'msg': 0})


@login_required
def start_ice_service(request, service_id):
    if not request.user.has_perm('services.deploy'):
        return JsonResponse({'msg': '你无权操作此项'})
    try:
        service = IceService.objects.get(id=service_id)
    except IceService.DoesNotExist:
        return JsonResponse({'msg': 'service: %s does not exist' % service_id})
    try:
        service.deploy()
    except Exception as e:
        return JsonResponse({'msg': unicode(e)})
    return JsonResponse({'msg': 0})


@login_required
def sync_ice_service_xml(request, service_id):
    if not request.user.has_perm('services.deploy'):
        return JsonResponse({'msg': '你无权操作此项'})
    try:
        service = IceService.objects.get(id=service_id)
    except IceService.DoesNotExist:
        return JsonResponse({'msg': 'service: %s does not exist' % service_id})
    try:
        service.sync_application_without_restart()
    except Exception as e:
        return JsonResponse({'msg': unicode(e)})
    return JsonResponse({'msg': 0})


@login_required
def remove_ice_service(request, service_id):
    if not request.user.has_perm('services.deploy'):
        return JsonResponse({'msg': '你无权操作此项'})
    try:
        service = IceService.objects.get(id=service_id)
    except IceService.DoesNotExist:
        return JsonResponse({'msg': 'service: %s does not exist' % service_id})
    try:
        service.remove_service()
    except Exception as e:
        return JsonResponse({'msg': unicode(e)})
    return JsonResponse({'msg': 0})


class ScriptCreate(PermissionRequiredMixin, CreateView):
    model = Script
    form_class = ScriptForm
    template_name = 'services/script_form.html'
    success_url = reverse_lazy('script_list')
    permission_required = 'services.add_script'
    raise_exception = True

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        self.object = Script.objects.create(name=cleaned_data['name'], script=cleaned_data['script'],
                                            server=cleaned_data['server'], owner=self.request.user,
                                            note=cleaned_data['note'])
        return HttpResponseRedirect(self.get_success_url())


class ScriptUpdate(PermissionRequiredMixin, UpdateView):
    model = Script
    form_class = ScriptForm
    context_object_name = 'script'
    template_name = 'services/script_form.html'
    permission_required = 'services.change_script'
    raise_exception = True


class ScriptDetail(LoginRequiredMixin, DetailView):
    model = Script
    context_object_name = 'script'
    template_name = 'services/script_detail.html'

    def get_context_data(self, **kwargs):
        context = super(ScriptDetail, self).get_context_data(**kwargs)
        context['has_perm_run_script'] = self.request.user.has_perm('services.run_script')
        return context


class ScriptDelete(PermissionRequiredMixin, DeleteView):
    model = Script
    context_object_name = 'script'
    template_name = 'services/script_confirm_delete.html'
    success_url = reverse_lazy('script_list')
    permission_required = 'services.delete_script'
    raise_exception = True


class ScriptList(LoginRequiredMixin, ListView):
    model = Script
    paginate_by = 20
    context_object_name = 'script_list'
    template_name = 'services/scripts.html'

    def get_queryset(self):
        queryset = super(ScriptList, self).get_queryset()
        user = self.request.user
        if user.profile.role.alias == 'developer':
            queryset = queryset.filter(owner=user)
        return queryset

    def get_context_data(self, **kwargs):
        context = super(ScriptList, self).get_context_data(**kwargs)
        context['has_perm_add_script'] = self.request.user.has_perm('services.add_script')
        return context


@login_required
def run_script(request, pk):
    if not request.user.has_perm('services.run_script'):
        return JsonResponse({'msg': '403 - 缺少权限'})
    try:
        script = Script.objects.get(id=pk)
    except Script.DoesNotExist:
        return JsonResponse({'msg': 'script: %s does not exist' % pk})
    if script.server.listen_ip not in RDS.keys():
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
    except User.DoesNotExist:
        return HttpResponseRedirect(reverse('script_list'))
    return render(request, 'services/script_implement_log_view.html', {'script': script})


def script_implement_log(request, identifier):
    ret = [RDS.lpop(identifier) for i in xrange(RDS.llen(identifier))]
    return JsonResponse({'msg': ret})
