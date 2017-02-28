# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import logging

import redis

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.shortcuts import render
from django.views.generic import CreateView, ListView, UpdateView, DetailView, DeleteView
from django.core.urlresolvers import reverse_lazy, reverse
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.conf import settings

from utils.mixins import LoginRequiredMixin, PermissionRequiredMixin

from .models import (
    IceServiceCenter, IceServiceNode, IceServiceConfig, IceServiceJar, IceService, Script,
    TomcatAppSql, TomcatServer, TomcatServerWarDir, TomcatAppWar, TomcatApp
)
from .forms import (
    IceServiceCenterForm, IceServiceNodeForm, IceServiceJarForm, IceServiceConfigForm,  IceServiceForm,
    ScriptForm, TomcatServerForm, TomcatServerWarDirForm, TomcatAppForm, TomcatAppWarForm, TomcatAppSqlForm
)
from .tasks import task_execute_sql, task_backup_db


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
        if user.profile.role.alias == 'developer' and user.profile.privilege < 3:
            ice_services = ice_services.filter(user=user)
        context['ice_service_list'] = ice_services
        context['ice_service_node_list'] = self.object.get_ice_nodes()
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
        context['active_jar'] = self.object.iceservicejar_set.filter(active=True).first()
        context['active_config'] = self.object.iceserviceconfig_set.filter(active=True).first()
        context['active_jar_count'] = self.object.iceservicejar_set.count()
        context['active_config_count'] = self.object.iceserviceconfig_set.count()
        return context


class IceServiceJarCreate(LoginRequiredMixin, CreateView):
    model = IceServiceJar
    form_class = IceServiceJarForm
    template_name = 'services/ice_service_jar_form.html'
    success_url = 'ice_service_jar_list'

    def get_initial(self):
        initial = super(IceServiceJarCreate, self).get_initial()
        self.ice_service = IceService.objects.get(id=self.args[0])
        initial['ice_service'] = self.ice_service
        initial['active'] = True
        return initial

    def get_context_data(self, **kwargs):
        context = super(IceServiceJarCreate, self).get_context_data(**kwargs)
        context['ice_service'] = self.ice_service
        return context

    def get_success_url(self):
        return reverse(self.success_url, kwargs={'ice_service_id': self.args[0]})

    def inactive_set(self):
        """将前面处于激活状态的关闭"""
        IceService.objects.get(id=self.args[0]).iceservicejar_set.filter(active=True).update(active=False)

    def form_valid(self, form):
        self.inactive_set()
        return super(IceServiceJarCreate, self).form_valid(form)


class IceServiceJarUpdate(LoginRequiredMixin, UpdateView):
    model = IceServiceJar
    form_class = IceServiceJarForm
    context_object_name = 'ice_service_jar'
    template_name = 'services/ice_service_jar_form.html'
    success_url = 'ice_service_jar_list'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user.profile.role.alias == 'developer' and self.object.ice_service.user != request.user:
            raise PermissionDenied('It is not your IceService')
        return super(IceServiceJarUpdate, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(self.success_url, kwargs={'ice_service_id': self.object.ice_service.id})

    def get_context_data(self, **kwargs):
        context = super(IceServiceJarUpdate, self).get_context_data(**kwargs)
        context['ice_service'] = self.object.ice_service
        return context


@login_required
def active_jar_package(request, pk):
    try:
        jar = IceServiceJar.objects.get(pk=pk)
    except IceServiceJar.DoesNotExist:
        return JsonResponse({'msg': 'jar does not exists'})
    old_active_jar = jar.ice_service.iceservicejar_set.filter(active=True).first()
    if old_active_jar and old_active_jar != jar:
        old_active_jar.active = False
        old_active_jar.save()
    jar.active = True
    jar.save()
    return JsonResponse({'msg': 0})


@login_required
def delete_jar_package(request, pk):
    try:
        jar = IceServiceJar.objects.get(pk=pk)
    except IceServiceJar.DoesNotExist:
        return JsonResponse({'msg': 'jar does not exists'})
    if jar.active:
        return JsonResponse({'msg': '这个程序包处于激活状态，不能删除！'})
    jar.delete()
    return JsonResponse({'msg': 0})


class IceServiceJarList(LoginRequiredMixin, ListView):
    model = IceServiceJar
    paginate_by = 20
    context_object_name = 'ice_service_jar_list'
    template_name = 'services/ice_service_jar_list.html'

    def get_queryset(self):
        queryset = super(IceServiceJarList, self).get_queryset()
        queryset = queryset.filter(ice_service=self.kwargs['ice_service_id'])
        return queryset.order_by('-create_time')

    def get_context_data(self, **kwargs):
        context = super(IceServiceJarList, self).get_context_data(**kwargs)
        try:
            ice_service = IceService.objects.get(pk=self.kwargs['ice_service_id'])
        except IceService.DoesNotExist:
            raise Http404
        context['ice_service'] = ice_service
        context['active_jar_count'] = ice_service.iceservicejar_set.count()
        context['active_config_count'] = ice_service.iceserviceconfig_set.count()
        return context


class IceServiceConfigCreate(IceServiceJarCreate):
    model = IceServiceConfig
    form_class = IceServiceConfigForm
    template_name = 'services/ice_service_config_form.html'
    success_url = 'ice_service_config_list'

    def inactive_set(self):
        IceService.objects.get(id=self.args[0]).iceserviceconfig_set.filter(active=True).update(active=False)


class IceServiceConfigUpdate(IceServiceJarUpdate):
    model = IceServiceConfig
    form_class = IceServiceConfigForm
    context_object_name = 'ice_service_config'
    template_name = 'services/ice_service_config_form.html'
    success_url = 'ice_service_config_list'


@login_required
def active_config(request, pk):
    try:
        conf = IceServiceConfig.objects.get(pk=pk)
    except IceServiceConfig.DoesNotExist:
        return JsonResponse({'msg': 'conf does not exists'})
    old_active_conf = conf.ice_service.iceserviceconfig_set.filter(active=True).first()
    if old_active_conf and conf != old_active_conf:
        old_active_conf.active = False
        old_active_conf.save()
    conf.active = True
    conf.save()
    return JsonResponse({'msg': 0})


@login_required
def delete_config(request, pk):
    try:
        conf = IceServiceConfig.objects.get(pk=pk)
    except IceServiceConfig.DoesNotExist:
        return JsonResponse({'msg': 'config does not exists'})
    if conf.active:
        return JsonResponse({'msg': '这个配置文件处于激活状态，不能删除！'})
    conf.delete()
    return JsonResponse({'msg': 0})


class IceServiceConfigList(IceServiceJarList):
    model = IceServiceConfig
    paginate_by = 20
    context_object_name = 'ice_service_config_list'
    template_name = 'services/ice_service_config_list.html'


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
def switch_ice_server_node_state(request, service_id, server, state):
    try:
        service = IceService.objects.get(id=service_id)
    except IceService.DoesNotExist:
        return JsonResponse({'msg': 'service: %s does not exist' % service_id})
    if not request.user.has_perm('services.deploy_service', service.center):
        return JsonResponse({'msg': '你无权操作此项'})
    try:
        if int(state):
            service.start_server(server)
        else:
            service.stop_server(server)
    except Exception as e:
        return JsonResponse({'msg': unicode(e)})
    return JsonResponse({'msg': 0})


@login_required
def push_pkg_to_node(request, service_id):
    node_name = request.GET.get('node')
    if node_name is None:
        return JsonResponse({'msg': 'param error'})
    try:
        service = IceService.objects.get(id=service_id)
    except IceService.DoesNotExist:
        return JsonResponse({'msg': 'service: %s does not exist' % service_id})
    if not request.user.has_perm('services.deploy_service', service.center):
        return JsonResponse({'msg': '你无权操作此项'})
    active_jar = service.get_active_jar()
    if not active_jar:
        return JsonResponse({'msg': '没有激活的jar包'})
    if not active_jar.finished:
        return JsonResponse({'msg': '激活的jar包还没有下载到web-server端, 无法推送！'})
    node_names = service.center.get_all_node_names() + ['all']
    if node_name not in node_names:
        return JsonResponse({'msg': 'node error'})
    try:
        if node_name == 'all':
            service.push_task_to_all_node()
        else:
            service.push_task_to_node(node_name)
    except Exception as e:
        errlog.exception('push task error')
        return JsonResponse({'msg': unicode(e)})
    return JsonResponse({'msg': 0})


@login_required
def start_ice_service(request, service_id):
    try:
        service = IceService.objects.get(id=service_id)
    except IceService.DoesNotExist:
        return JsonResponse({'msg': 'service: %s does not exist' % service_id})
    if not request.user.has_perm('services.deploy_service', service.center):
        return JsonResponse({'msg': '你无权操作此项'})
    try:
        service.deploy()
    except Exception as e:
        return JsonResponse({'msg': unicode(e)})
    return JsonResponse({'msg': 0})


@login_required
def sync_ice_service_xml(request, service_id):
    try:
        service = IceService.objects.get(id=service_id)
    except IceService.DoesNotExist:
        return JsonResponse({'msg': 'service: %s does not exist' % service_id})
    if not request.user.has_perm('services.deploy_service', service.center):
        return JsonResponse({'msg': '你无权操作此项'})
    try:
        service.sync_application_without_restart()
    except Exception as e:
        return JsonResponse({'msg': unicode(e)})
    return JsonResponse({'msg': 0})


@login_required
def remove_ice_service(request, service_id):
    try:
        service = IceService.objects.get(id=service_id)
    except IceService.DoesNotExist:
        return JsonResponse({'msg': 'service: %s does not exist' % service_id})
    if not request.user.has_perm('services.deploy_service', service.center):
        return JsonResponse({'msg': '你无权操作此项'})
    try:
        service.remove_service()
    except Exception as e:
        return JsonResponse({'msg': unicode(e)})
    return JsonResponse({'msg': 0})


class TomcatServerCreate(PermissionRequiredMixin, CreateView):
    model = TomcatServerForm
    form_class = TomcatServerForm
    template_name = 'services/tomcat_server_form.html'
    success_url = reverse_lazy('tomcat_server_list')
    permission_required = 'services.add_tomcatserver'


class TomcatServerUpdate(PermissionRequiredMixin, UpdateView):
    model = TomcatServer
    form_class = TomcatServerForm
    context_object_name = 'tomcat_server'
    template_name = 'services/tomcat_server_form.html'
    permission_required = 'services.change_tomcatserver'


class TomcatServerDetail(LoginRequiredMixin, DetailView):
    model = TomcatServer
    context_object_name = 'tomcat_server'
    template_name = 'services/tomcat_server_detail.html'

    def get_context_data(self, **kwargs):
        context = super(TomcatServerDetail, self).get_context_data(**kwargs)
        user = self.request.user
        tomcat_apps = self.object.tomcatapp_set.all()
        if user.profile.role.alias == 'developer' and user.profile.privilege < 3:
            tomcat_apps = tomcat_apps.filter(user=user)
        context['tomcat_app_list'] = tomcat_apps
        try:
            context['is_alive'] = self.object.is_alive()
        except IOError:
            context['is_alive'] = False
            messages.error(self.request, '无法连接到Tomcat-server')
        return context


class TomcatServerDelete(PermissionRequiredMixin, DeleteView):
    model = TomcatServer
    context_object_name = 'tomcat_server'
    template_name = 'services/tomcat_server_confirm_delete.html'
    success_url = reverse_lazy('tomcat_server_list')
    permission_required = 'services.delete_tomcatserver'


class TomcatServerList(LoginRequiredMixin, ListView):
    model = TomcatServer
    context_object_name = 'tomcat_server_list'
    template_name = 'services/tomcat_server_list.html'


@login_required
def tomcat_server_switch(request, pk):
    try:
        ts = TomcatServer.objects.get(pk=pk)
    except TomcatServer.DoesNotExist:
        return JsonResponse({'msg': 'TomcatServer does not exists'})
    state = request.GET.get('state')
    if state not in ('start', 'stop'):
        return JsonResponse({'msg': 'State ValueError'})
    if not request.user.has_perm('services.operate_tomcat', ts):
        return JsonResponse({'msg': '你无权操作此项'})
    try:
        if state == 'start':
            ret = ts.start()
        else:
            ret = ts.kill()
        if not ret:
            raise RuntimeError('%s tomcat-server error' % state)
    except (IOError, RuntimeError) as e:
        return JsonResponse({'msg': unicode(e)})
    return JsonResponse({'msg': 0})


class TomcatServerWarDirCreate(PermissionRequiredMixin, CreateView):
    model = TomcatServerWarDir
    form_class = TomcatServerWarDirForm
    template_name = 'services/tomcat_server_war_dri_form.html'
    permission_required = 'services.add_tomcatserverwardir'

    def get_initial(self):
        initial = super(TomcatServerWarDirCreate, self).get_initial()
        self.tomcat_server = TomcatServer.objects.get(pk=self.kwargs['tomcat_server_id'])
        initial['tomcat_server'] = self.tomcat_server
        return initial

    def get_success_url(self):
        return reverse('tomcat_server_detail', kwargs={'pk': self.kwargs['tomcat_server_id']})

    def get_context_data(self, **kwargs):
        context = super(TomcatServerWarDirCreate, self).get_context_data(**kwargs)
        context['tomcat_server'] = self.tomcat_server
        return context


class TomcatServerWarDirUpdate(PermissionRequiredMixin, UpdateView):
    model = TomcatServerWarDir
    form_class = TomcatServerWarDirForm
    context_object_name = 'tomcat_server_war_dir'
    template_name = 'services/tomcat_server_war_dri_form.html'
    permission_required = 'services.change_tomcatserverwardir'

    def get_success_url(self):
        return reverse('tomcat_server_detail', kwargs={'pk': self.object.tomcat_server.id})


class TomcatServerWarDirDelete(PermissionRequiredMixin, DeleteView):
    model = TomcatServerWarDir
    context_object_name = 'tomcat_server_war_dir'
    template_name = 'services/tomcat_server_war_dir_confirm_delete.html'
    permission_required = 'services.delete_tomcatserverwardir'

    def get_success_url(self):
        return reverse('tomcat_server_detail', kwargs={'pk': self.object.tomcat_server.id})


class TomcatAppCreate(PermissionRequiredMixin, CreateView):
    model = TomcatApp
    form_class = TomcatAppForm
    template_name = 'services/tomcat_app_form.html'
    permission_required = 'services.add_tomcatapp'

    def get_initial(self):
        initial = super(TomcatAppCreate, self).get_initial()
        self.tomcat_server = TomcatServer.objects.get(pk=self.kwargs['tomcat_server_id'])
        initial['tomcat_server'] = self.tomcat_server
        initial['user'] = self.request.user
        return initial

    def get_success_url(self):
        return reverse('tomcat_server_detail', kwargs={'pk': self.kwargs['tomcat_server_id']})

    def get_context_data(self, **kwargs):
        context = super(TomcatAppCreate, self).get_context_data(**kwargs)
        context['tomcat_server'] = self.tomcat_server
        return context


class TomcatAppUpdate(PermissionRequiredMixin, UpdateView):
    model = TomcatApp
    form_class = TomcatAppForm
    context_object_name = 'tomcat_app'
    template_name = 'services/tomcat_app_form.html'
    permission_required = 'services.change_tomcatapp'

    def get_initial(self):
        initial = super(TomcatAppUpdate, self).get_initial()
        initial['tomcat_server'] = self.object.tomcat_server
        initial['user'] = self.request.user
        return initial


class TomcatAppDetail(LoginRequiredMixin, DetailView):
    model = TomcatApp
    context_object_name = 'tomcat_app'
    template_name = 'services/tomcat_app_detail.html'


class TomcatAppDelete(PermissionRequiredMixin, DeleteView):
    model = TomcatApp
    context_object_name = 'tomcat_app'
    template_name = 'services/tomcat_app_confirm_delete.html'
    permission_required = 'services.delete_tomcatapp'

    def get_success_url(self):
        return reverse('tomcat_server_detail', kwargs={'pk': self.object.tomcat_server.id})


@login_required
def backup_database(request, tomcat_app_id):
    try:
        app = TomcatApp.objects.get(pk=tomcat_app_id)
    except TomcatApp.DoesNotExist:
        return JsonResponse({'msg': 'TomcatApp: %s does not exists' % tomcat_app_id})
    if not app.db_is_enabled:
        return JsonResponse({'msg': '数据库设置不完整!'})
    if not request.user.has_perm('services.operate_db', app.tomcat_server):
        return JsonResponse({'msg': '你无权操作此项'})
    if app.bak_flag:
        return JsonResponse({'msg': '系统正在备份该Tomcat应用的数据库, 稍等!'})
    app.bak_flag = True
    app.save()
    task_backup_db.delay(tomcat_app_id)
    return JsonResponse({'msg': 0})


class TomcatAppWarCreate(PermissionRequiredMixin, CreateView):
    model = TomcatAppWar
    form_class = TomcatAppWarForm
    template_name = 'services/tomcat_app_war_form.html'
    success_url = 'tomcat_app_war_list'
    permission_required = 'services.add_tomcatappwar'

    def get_success_url(self):
        return reverse(self.success_url, kwargs={'tomcat_app_id': self.object.tomcat_app.id})

    def get_initial(self):
        initial = super(TomcatAppWarCreate, self).get_initial()
        self.tomcat_app = TomcatApp.objects.get(pk=self.args[0])
        initial['tomcat_app'] = self.tomcat_app
        return initial

    def get_context_data(self, **kwargs):
        context = super(TomcatAppWarCreate, self).get_context_data(**kwargs)
        context['tomcat_app'] = self.tomcat_app
        return context


class TomcatAppWarUpdate(PermissionRequiredMixin, UpdateView):
    model = TomcatAppWar
    form_class = TomcatAppWarForm
    context_object_name = 'tomcat_app_war'
    template_name = 'services/tomcat_app_war_form.html'
    success_url = 'tomcat_app_war_list'
    permission_required = 'services.change_tomcatappwar'
    dirty_state = [1]

    def get_success_url(self):
        return reverse(self.success_url, kwargs={'tomcat_app_id': self.object.tomcat_app.id})

    def get_context_data(self, **kwargs):
        context = super(TomcatAppWarUpdate, self).get_context_data(**kwargs)
        context['tomcat_app'] = self.object.tomcat_app
        return context

    def form_valid(self, form):
        if self.object.state not in self.dirty_state:
            return super(TomcatAppWarUpdate, self).form_valid(form)
        else:
            return HttpResponseRedirect(self.get_success_url())


class TomcatAppWarDelete(PermissionRequiredMixin, DeleteView):
    model = TomcatAppWar
    context_object_name = 'tomcat_app_war'
    template_name = 'services/tomcat_app_war_confirm_delete.html'
    success_url = 'tomcat_app_war_list'
    permission_required = 'services.delete_tomcatappwar'
    dirty_state = [1]

    def get_success_url(self):
        return reverse(self.success_url, kwargs={'tomcat_app_id': self.object.tomcat_app.id})

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        if self.object.state not in self.dirty_state:
            # 如果任务正在celery中执行, 则不能删除
            self.object.delete()
        return HttpResponseRedirect(success_url)


class TomcatAppWarList(LoginRequiredMixin, ListView):
    model = TomcatAppWar
    paginate_by = 10
    context_object_name = 'tomcat_app_war_list'
    template_name = 'services/tomcat_app_war_list.html'

    def get_queryset(self):
        queryset = super(TomcatAppWarList, self).get_queryset()
        queryset = queryset.filter(tomcat_app__id=self.kwargs['tomcat_app_id'])
        return queryset.order_by('-create_time')

    def get_context_data(self, **kwargs):
        context = super(TomcatAppWarList, self).get_context_data(**kwargs)
        try:
            context['tomcat_app'] = TomcatApp.objects.get(pk=self.kwargs['tomcat_app_id'])
        except TomcatApp.DoesNotExist:
            raise Http404
        return context


@login_required
def push_war_to_tomcat(request, pk):
    try:
        war = TomcatAppWar.objects.get(id=pk)
    except TomcatAppWar.DoesNotExist:
        return JsonResponse({'msg': 'TomcatAppWar: %s does not exists' % pk})
    if not request.user.has_perm('services.push_war_pkg', war.tomcat_app.tomcat_server):
        return JsonResponse({'msg': '你无权操作此项'})
    if not war.is_ready:
        return JsonResponse({'msg': 'Marmot正在下载地址中的War包，请稍等!'})
    try:
        war.push_to_tomcat()
    except IOError:
        return JsonResponse({
            'msg': '服务器无法连接: %s -- %s' % (war.tomcat_app.tomcat_server.name, war.tomcat_app.tomcat_server.host)
        })
    return JsonResponse({
        'msg': 0,
        'redirect': reverse('node_task_log_view', args=[war.tomcat_app.hex_identifier])
    })


class TomcatAppSqlCreate(TomcatAppWarCreate):
    model = TomcatAppSql
    form_class = TomcatAppSqlForm
    template_name = 'services/tomcat_app_sql_form.html'
    success_url = 'tomcat_app_sql_list'
    permission_required = 'services.add_tomcatappsql'


class TomcatAppSqlUpdate(TomcatAppWarUpdate):
    model = TomcatAppSql
    form_class = TomcatAppSqlForm
    context_object_name = 'tomcat_app_sql'
    template_name = 'services/tomcat_app_sql_form.html'
    success_url = 'tomcat_app_sql_list'
    permission_required = 'services.change_tomcatappsql'
    dirty_state = [2]


class TomcatAppSqlDelete(TomcatAppWarDelete):
    model = TomcatAppSql
    context_object_name = 'tomcat_app_sql'
    template_name = 'services/tomcat_app_sql_confirm_delete.html'
    success_url = 'tomcat_app_sql_list'
    permission_required = 'services.delete_tomcatappsql'
    dirty_state = [2]


class TomcatAppSqlList(TomcatAppWarList):
    model = TomcatAppSql
    context_object_name = 'tomcat_app_sql_list'
    template_name = 'services/tomcat_app_sql_list.html'


@login_required
def execute_sql(request, pk):
    try:
        sql = TomcatAppSql.objects.get(pk=pk)
    except TomcatAppSql.DoesNotExist:
        return JsonResponse({'msg': 'TomcatAppSql: %s done not exists!' % pk})
    if not sql.tomcat_app.db_is_enabled:
        return JsonResponse({'msg': '数据库设置不完整!'})
    if not request.user.has_perm('services.operate_db', sql.tomcat_app.tomcat_server):
        return JsonResponse({'msg': '你无权操作此项'})
    if sql.state == 2:
        return JsonResponse({'msg': '此sql正在执行队列中!'})
    if sql.tomcat_app.bak_flag:
        return JsonResponse({'msg': '系统正在备份Tomcat应用 "%s" 的数据库, 暂时不能执行sql' % sql.tomcat_app.name})
    if sql.tomcat_app.tomcatappsql_set.filter(state=2).exists():
        return JsonResponse({'msg': '该Tomcat应用中, 有其他sql文件正在执行, 请稍后!'})
    if not os.path.isfile(sql.sql.path):
        return JsonResponse({'msg': 'sql文件: %s 不存在!' % sql.sql.name})
    sql.state = 2  # 标记该sql正在执行
    sql.save()
    task_execute_sql.delay(sql.id)
    return JsonResponse({'msg': 0})


class ScriptCreate(PermissionRequiredMixin, CreateView):
    model = Script
    form_class = ScriptForm
    template_name = 'services/script_form.html'
    success_url = reverse_lazy('script_list')
    permission_required = 'services.add_script'
    raise_exception = True

    def get_initial(self):
        initial = super(ScriptCreate, self).get_initial()
        initial['owner'] = self.request.user
        return initial

    # def form_valid(self, form):
    #     cleaned_data = form.cleaned_data
    #     print form.changed_data
    #     self.object = Script.objects.create(name=cleaned_data['name'], script=cleaned_data['script'],
    #                                         server=cleaned_data['server'], owner=self.request.user,
    #                                         note=cleaned_data['note'])
    #     return HttpResponseRedirect(self.get_success_url())


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
    if script.server.ip not in RDS.keys():
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
