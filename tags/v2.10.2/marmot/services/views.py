# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import xmlrpclib
import httplib
import logging

import redis

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.views.generic import FormView, CreateView, ListView, UpdateView, DetailView, DeleteView
from django.core.urlresolvers import reverse_lazy, reverse
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.db.utils import IntegrityError
from django.conf import settings

from utils.mixins import LoginRequiredMixin, PermissionRequiredMixin

from .models import (
    IceServiceCenter, IceServiceConfig, IceServiceJar, IceService,
    TomcatGroup, TomcatCluster, TomcatServer, TomcatServerWarDir,
    TomcatApp, TomcatAppNode, TomcatAppSql, TomcatAppWar, TomcatAppStatic, TomcatAppDB
)
from .forms import (
    IceServiceCenterForm, IceServiceJarForm, IceServiceConfigForm, IceServiceForm, IceServiceUpdateForm,
    TomcatGroupForm, TomcatClusterForm, TomcatServerForm, TomcatServerWarDirForm,
    TomcatAppForm, TomcatAppUpdateForm, TomcatAppWarForm, TomcatAppDBForm, TomcatAppSqlForm, TomcatAppStaticForm
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


class IceServiceCenterUpdate(PermissionRequiredMixin, UpdateView):
    model = IceServiceCenter
    form_class = IceServiceCenterForm
    context_object_name = 'ice_service_center'
    template_name = 'services/ice_service_center_form.html'
    permission_required = 'services.change_iceservicecenter'


class IceServiceCenterDetail(LoginRequiredMixin, DetailView):
    model = IceServiceCenter
    context_object_name = 'ice_service_center'
    template_name = 'services/ice_service_center_detail.html'

    def get_context_data(self, **kwargs):
        context = super(IceServiceCenterDetail, self).get_context_data(**kwargs)
        user = self.request.user
        ice_services = self.object.iceservice_set.all()
        if user.profile.role.alias == 'developer' and user.profile.privilege < 3:
            ice_services = ice_services.filter(users=user)
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


class IceServiceCenterList(LoginRequiredMixin, ListView):
    model = IceServiceCenter
    context_object_name = 'ice_service_center_list'
    template_name = 'services/ice_service_center_list.html'


class IceServiceCreate(PermissionRequiredMixin, CreateView):
    model = IceService
    form_class = IceServiceForm
    template_name = 'services/ice_service_form.html'
    permission_required = 'services.add_iceservice'

    def get_initial(self):
        initial = super(IceServiceCreate, self).get_initial()
        self.center = IceServiceCenter.objects.get(id=self.args[0])
        initial['center'] = self.center
        initial['users'] = [self.request.user]
        return initial

    def get_context_data(self, **kwargs):
        context = super(IceServiceCreate, self).get_context_data(**kwargs)
        context['center'] = self.center
        return context

    def get_success_url(self):
        return self.center.get_absolute_url()


class IceServiceUpdate(PermissionRequiredMixin, UpdateView):
    model = IceService
    form_class = IceServiceUpdateForm
    context_object_name = 'ice_service'
    template_name = 'services/ice_service_form.html'
    permission_required = 'services.change_iceservice'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user.profile.role.alias == 'developer' and \
                        request.user.profile.privilege < 3 and \
                        request.user not in self.object.users.all():
            raise PermissionDenied('this is not your IceService')
        return super(IceServiceUpdate, self).dispatch(request, *args, **kwargs)


class IceServiceDetail(LoginRequiredMixin, DetailView):
    model = IceService
    context_object_name = 'ice_service'
    template_name = 'services/ice_service_detail.html'

    def get_context_data(self, **kwargs):
        context = super(IceServiceDetail, self).get_context_data(**kwargs)
        context['application_nodes'] = self.object.get_application_servers()
        context['active_jar'] = self.object.iceservicejar_set.filter(active=True).first()
        context['active_config'] = self.object.iceserviceconfig_set.filter(active=True).first()
        context['active_jar_count'] = self.object.iceservicejar_set.count()
        context['active_config_count'] = self.object.iceserviceconfig_set.count()
        if context['active_jar_count'] == 0 and context['active_config_count'] == 0:
            messages.warning(self.request, '请注意上传Jar包和配置文件(如果有)！')
        return context


class IceServiceDelete(PermissionRequiredMixin, DeleteView):
    model = IceService
    context_object_name = 'ice_service'
    template_name = 'services/ice_service_confirm_delete.html'
    permission_required = 'services.delete_iceservice'

    def get_success_url(self):
        return self.object.center.get_absolute_url()

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user.profile.role.alias == 'developer' and \
                        request.user.profile.privilege < 3 and \
                        request.user not in self.object.users.all():
            raise PermissionDenied('This is not your IceService')
        return super(IceServiceDelete, self).dispatch(request, *args, **kwargs)


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
        initial['user'] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super(IceServiceJarCreate, self).get_context_data(**kwargs)
        context['ice_service'] = self.ice_service
        return context

    def get_success_url(self):
        return reverse(self.success_url, kwargs={'ice_service_id': self.args[0]})

    def inactive_set(self):
        """将前面处于激活状态的关闭"""
        self.ice_service.iceservicejar_set.filter(active=True).update(active=False)

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
        if request.user.profile.role.alias == 'developer' and request.user.profile.privilege < 3 and \
                        request.user not in self.object.ice_service.users.all():
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

    def get_initial(self):
        initial = super(IceServiceConfigCreate, self).get_initial()
        initial['user'] = self.request.user
        return initial

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
        return JsonResponse({'msg': 'Node name error!'})
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
        return JsonResponse({'msg': '激活的jar包还没有下载到WebServer端, 无法推送！'})
    node_names = service.center.get_all_node_names() + ['all']
    if node_name not in node_names:
        return JsonResponse({'msg': 'node error'})
    try:
        if node_name == 'all':
            service.push_task_to_all_node()
        else:
            service.push_task_to_node(node_name)
    except Exception as e:
        errlog.exception('Push task error')
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


class TomcatGroupCreate(PermissionRequiredMixin, CreateView):
    model = TomcatGroup
    form_class = TomcatGroupForm
    template_name = 'services/tomcat_group_form.html'
    success_url = reverse_lazy('tomcat_group_list')
    permission_required = 'services.add_tomcatgroup'


class TomcatGroupUpdate(PermissionRequiredMixin, UpdateView):
    model = TomcatGroup
    form_class = TomcatGroupForm
    context_object_name = 'tomcat_group'
    template_name = 'services/tomcat_group_form.html'
    permission_required = 'services.change_tomcatgroup'


class TomcatGroupDetail(LoginRequiredMixin, DetailView):
    model = TomcatGroup
    context_object_name = 'tomcat_group'
    template_name = 'services/tomcat_group_detail.html'

    def get_context_data(self, **kwargs):
        context = super(TomcatGroupDetail, self).get_context_data(**kwargs)
        context['tomcat_cluster_list'] = self.object.tomcatcluster_set.all()
        return context


class TomcatGroupDelete(PermissionRequiredMixin, DeleteView):
    model = TomcatGroup
    context_object_name = 'tomcat_group'
    template_name = 'services/tomcat_group_confirm_delete.html'
    success_url = reverse_lazy('tomcat_group_list')
    permission_required = 'services.delete_tomcatgroup'


class TomcatGroupList(LoginRequiredMixin, ListView):
    model = TomcatGroup
    context_object_name = 'tomcat_group_list'
    template_name = 'services/tomcat_group_list.html'


class TomcatClusterCreate(PermissionRequiredMixin, CreateView):
    model = TomcatCluster
    form_class = TomcatClusterForm
    template_name = 'services/tomcat_cluster_form.html'
    permission_required = 'services.add_tomcatcluster'

    def get_initial(self):
        initial = super(TomcatClusterCreate, self).get_initial()
        self.group = get_object_or_404(TomcatGroup, id=self.args[0])
        initial['group'] = self.group
        initial['user'] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super(TomcatClusterCreate, self).get_context_data(**kwargs)
        context['group'] = self.group
        return context

    def get_success_url(self):
        return self.group.get_absolute_url()


class TomcatClusterUpdate(PermissionRequiredMixin, UpdateView):
    model = TomcatCluster
    form_class = TomcatClusterForm
    context_object_name = 'tomcat_cluster'
    template_name = 'services/tomcat_cluster_form.html'
    permission_required = 'services.change_tomcatcluster'


class TomcatClusterDetail(LoginRequiredMixin, DetailView):
    model = TomcatCluster
    context_object_name = 'tomcat_cluster'
    template_name = 'services/tomcat_cluster_detail.html'

    def get_context_data(self, **kwargs):
        context = super(TomcatClusterDetail, self).get_context_data(**kwargs)
        user = self.request.user
        if user.profile.role.alias == 'developer' and user.profile.privilege < 3:
            context['tomcat_app_list'] = self.object.tomcatapp_set.filter(users=user).all()
        else:
            context['tomcat_app_list'] = self.object.tomcatapp_set.all()
        return context


class TomcatClusterDelete(PermissionRequiredMixin, DeleteView):
    model = TomcatCluster
    context_object_name = 'tomcat_cluster'
    template_name = 'services/tomcat_cluster_confirm_delete.html'
    permission_required = 'services.delete_tomcatcluster'

    def get_success_url(self):
        return self.object.group.get_absolute_url()


class TomcatServerCreate(PermissionRequiredMixin, CreateView):
    model = TomcatServer
    form_class = TomcatServerForm
    template_name = 'services/tomcat_server_form.html'
    permission_required = 'services.add_tomcatserver'

    def get_initial(self):
        initial = super(TomcatServerCreate, self).get_initial()
        self.cluster = get_object_or_404(TomcatCluster, id=self.args[0])
        initial['cluster'] = self.cluster
        initial['user'] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super(TomcatServerCreate, self).get_context_data(**kwargs)
        context['cluster'] = self.cluster
        return context

    def get_success_url(self):
        return self.object.cluster.get_absolute_url()


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
        context['is_alive'] = self.object.is_alive()
        return context


class TomcatServerDelete(PermissionRequiredMixin, DeleteView):
    model = TomcatServer
    context_object_name = 'tomcat_server'
    template_name = 'services/tomcat_server_confirm_delete.html'
    permission_required = 'services.delete_tomcatserver'

    def get_success_url(self):
        return self.object.cluster.get_absolute_url()


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
    if not request.user.has_perm('services.operate_tomcat', ts.cluster):
        return JsonResponse({'msg': '你无权操作此项'})
    if state == 'start':
        ret = ts.start()
    else:
        ret = ts.kill()
    if not ret:
        return JsonResponse({'msg': '%s tomcat-server error' % state})
    return JsonResponse({'msg': 0})


class TomcatServerWarDirCreate(PermissionRequiredMixin, CreateView):
    model = TomcatServerWarDir
    form_class = TomcatServerWarDirForm
    template_name = 'services/tomcat_server_war_dir_form.html'
    permission_required = 'services.add_tomcatserverwardir'

    def get_initial(self):
        initial = super(TomcatServerWarDirCreate, self).get_initial()
        self.tomcat_server = TomcatServer.objects.get(pk=self.args[0])
        initial['tomcat_server'] = self.tomcat_server
        return initial

    def get_success_url(self):
        return reverse('tomcat_server_detail', kwargs={'pk': self.args[0]})

    def get_context_data(self, **kwargs):
        context = super(TomcatServerWarDirCreate, self).get_context_data(**kwargs)
        context['tomcat_server'] = self.tomcat_server
        return context


class TomcatServerWarDirUpdate(PermissionRequiredMixin, UpdateView):
    model = TomcatServerWarDir
    form_class = TomcatServerWarDirForm
    context_object_name = 'tomcat_server_war_dir'
    template_name = 'services/tomcat_server_war_dir_form.html'
    permission_required = 'services.change_tomcatserverwardir'

    def get_success_url(self):
        return self.object.tomcat_server.get_absolute_url()


class TomcatServerWarDirDelete(PermissionRequiredMixin, DeleteView):
    model = TomcatServerWarDir
    context_object_name = 'tomcat_server_war_dir'
    template_name = 'services/tomcat_server_war_dir_confirm_delete.html'
    permission_required = 'services.delete_tomcatserverwardir'

    def get_success_url(self):
        return self.object.tomcat_server.get_absolute_url()


class TomcatAppCreate(PermissionRequiredMixin, FormView):
    form_class = TomcatAppForm
    template_name = 'services/tomcat_app_form.html'
    permission_required = 'services.add_tomcatapp'

    def get_initial(self):
        initial = super(TomcatAppCreate, self).get_initial()
        self.tomcat_cluster = get_object_or_404(TomcatCluster, id=self.args[0])
        initial['cluster'] = self.tomcat_cluster
        return initial

    def get_form(self, form_class=None):
        form = super(TomcatAppCreate, self).get_form(form_class=form_class)
        form.fields['servers'].queryset = self.tomcat_cluster.tomcatserver_set.all()
        return form

    def get_success_url(self):
        return self.tomcat_cluster.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super(TomcatAppCreate, self).get_context_data(**kwargs)
        context['tomcat_cluster'] = self.tomcat_cluster
        return context

    def form_valid(self, form):
        app = TomcatApp(
            cluster=form.cleaned_data['cluster'], name=form.cleaned_data['name'],
            note=form.cleaned_data['note']
        )
        try:
            app.save()
        except IntegrityError:
            form.add_error('name', '该Tomcat集群下已经存在同名应用: %s' % form.cleaned_data['name'])
            return self.render_to_response(self.get_context_data(form=form))

        app.users.add(self.request.user)

        TomcatAppNode.objects.bulk_create(
            [TomcatAppNode(app=app, server=server) for server in form.cleaned_data['servers']]
        )
        return super(TomcatAppCreate, self).form_valid(form)


class TomcatAppUpdate(PermissionRequiredMixin, FormView):
    form_class = TomcatAppUpdateForm
    template_name = 'services/tomcat_app_form.html'
    permission_required = 'services.change_tomcatapp'

    def get_initial(self):
        initial = super(TomcatAppUpdate, self).get_initial()
        self.object = get_object_or_404(TomcatApp, pk=self.kwargs['pk'])
        initial['cluster'] = self.object.cluster
        initial['name'] = self.object.name
        initial['note'] = self.object.note
        initial['servers'] = [node.server for node in self.object.tomcatappnode_set.all()]
        initial['users'] = self.object.users.all()
        return initial

    def get_form(self, form_class=None):
        form = super(TomcatAppUpdate, self).get_form(form_class=form_class)
        form.fields['servers'].queryset = self.object.cluster.tomcatserver_set.all()
        return form

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super(TomcatAppUpdate, self).get_context_data(**kwargs)
        context['tomcat_app'] = self.object
        return context

    def form_valid(self, form):
        if form.has_changed():
            self.object.name = form.cleaned_data['name']
            self.object.note = form.cleaned_data['note']
            try:
                self.object.save()
            except IntegrityError:
                form.add_error('name', '该Tomcat集群下已经存在同名应用: %s' % form.cleaned_data['name'])
                return self.render_to_response(self.get_context_data(form=form))

            self.object.users.clear()
            self.object.users.add(*form.cleaned_data['users'])

            old_servers = [node.server for node in self.object.tomcatappnode_set.all()]
            now_servers = form.cleaned_data['servers']
            for node in self.object.tomcatappnode_set.all():
                if node.server not in now_servers:
                    node.delete()
            new_servers = []
            for server in now_servers:
                if server not in old_servers:
                    new_servers.append(server)
            new_app_node = [TomcatAppNode(app=self.object, server=server) for server in new_servers]
            if new_app_node:
                TomcatAppNode.objects.bulk_create(new_app_node)
        return super(TomcatAppUpdate, self).form_valid(form)


class TomcatAppDetail(LoginRequiredMixin, DetailView):
    model = TomcatApp
    context_object_name = 'tomcat_app'
    template_name = 'services/tomcat_app_detail.html'

    def get_context_data(self, **kwargs):
        context = super(TomcatAppDetail, self).get_context_data(**kwargs)
        context['active_war'] = self.object.tomcatappwar_set.filter(active=True).first()
        context['active_static'] = self.object.tomcatappstatic_set.filter(active=True).first()
        return context


class TomcatAppDelete(PermissionRequiredMixin, DeleteView):
    model = TomcatApp
    context_object_name = 'tomcat_app'
    template_name = 'services/tomcat_app_confirm_delete.html'
    permission_required = 'services.delete_tomcatapp'

    def get_success_url(self):
        return self.object.cluster.get_absolute_url()


@login_required
def config_tomcat_app_node_war_dir(request):
    tomcat_app_node_id = request.GET.get('nid')
    war_dir_id = request.GET.get('wid')
    if war_dir_id is None or tomcat_app_node_id is None:
        return JsonResponse({'msg': 'ValueError'})
    try:
        ts_war_dir = TomcatServerWarDir.objects.get(id=war_dir_id)
    except TomcatServerWarDir.DoesNotExist:
        return JsonResponse({'msg': 'TomcatServerWarDir: %s does not exist' % war_dir_id})
    try:
        tomcat_app_node = TomcatAppNode.objects.get(id=tomcat_app_node_id)
    except TomcatAppNode.DoesNotExist:
        return JsonResponse({'msg': 'TomcatAppNode: %s does not exist' % tomcat_app_node_id})
    tomcat_app_node.war_dir = ts_war_dir
    tomcat_app_node.save()
    return JsonResponse({'msg': 0})


@login_required
def get_tomcat_server_war_dir(request, nid):
    try:
        tomcat_app_node = TomcatAppNode.objects.get(id=nid)
    except TomcatAppNode.DoesNotExist:
        return JsonResponse({'msg': 'TomcatAppNode: %s does not exist' % nid})
    tsw_list = tomcat_app_node.server.tomcatserverwardir_set.all()
    return JsonResponse({
        'msg': 0, 'nid': nid,
        'data': [{'tswid': tsw.id, 'wdir': tsw.war_dir} for tsw in tsw_list]
    })


@login_required
def backup_database(request, db_id):
    try:
        db = TomcatAppDB.objects.get(pk=db_id)
    except TomcatAppDB.DoesNotExist:
        return JsonResponse({'msg': 'TomcatAppDB: %s does not exists' % db_id})
    if not db.is_ready:
        return JsonResponse({'msg': '该数据库正在备份或执行SQL, 稍等!'})
    if not request.user.has_perm('services.operate_db', db.app.cluster):
        return JsonResponse({'msg': '你无权操作此项'})
    db.state = 2  # 正在备份
    db.save()
    try:
        task_backup_db.delay(db.id)
    except redis.ConnectionError:
        db.state = 1  # 空闲
        db.save()
        return JsonResponse({'msg': 'Redis-ConnectionError'})
    return JsonResponse({'msg': 0})


class TomcatAppWarCreate(PermissionRequiredMixin, CreateView):
    model = TomcatAppWar
    form_class = TomcatAppWarForm
    template_name = 'services/tomcat_app_war_form.html'
    success_url = 'tomcat_app_war_list'
    permission_required = 'services.add_tomcatappwar'

    def get_success_url(self):
        return reverse(self.success_url, args=[self.object.tomcat_app.id])

    def get_initial(self):
        initial = super(TomcatAppWarCreate, self).get_initial()
        self.tomcat_app = TomcatApp.objects.get(pk=self.args[0])
        initial['tomcat_app'] = self.tomcat_app
        initial['active'] = True
        initial['user'] = self.request.user  # 这是为了初始化form中的user字段
        return initial

    def get_context_data(self, **kwargs):
        context = super(TomcatAppWarCreate, self).get_context_data(**kwargs)
        context['tomcat_app'] = self.tomcat_app
        return context

    def inactive_set(self):
        """将前面处于激活状态的关闭"""
        self.tomcat_app.tomcatappwar_set.filter(active=True).update(active=False)

    def form_valid(self, form):
        self.inactive_set()
        return super(TomcatAppWarCreate, self).form_valid(form)


class TomcatAppWarUpdate(PermissionRequiredMixin, UpdateView):
    model = TomcatAppWar
    form_class = TomcatAppWarForm
    context_object_name = 'tomcat_app_war'
    template_name = 'services/tomcat_app_war_form.html'
    success_url = 'tomcat_app_war_list'
    permission_required = 'services.change_tomcatappwar'
    dirty_state = [1]

    def get_initial(self):
        initial = super(TomcatAppWarUpdate, self).get_initial()
        initial['user'] = self.request.user
        return initial

    def get_success_url(self):
        return reverse(self.success_url, args=[self.object.tomcat_app.id])

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
    dirty_state = [1]  # 处在这个状态不允许删除

    def get_success_url(self):
        return reverse(self.success_url, args=[self.object.tomcat_app.id])

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.state not in self.dirty_state and not self.object.active:
            # 如果任务正在celery中执行或激活状态, 则不能删除
            self.object.delete()
        return HttpResponseRedirect(self.get_success_url())


class TomcatAppWarList(LoginRequiredMixin, ListView):
    model = TomcatAppWar
    paginate_by = 10
    template_name = 'services/tomcat_app_war_list.html'

    def get_queryset(self):
        queryset = super(TomcatAppWarList, self).get_queryset()
        queryset = queryset.filter(tomcat_app__id=self.args[0])
        return queryset.order_by('-create_time')

    def get_context_data(self, **kwargs):
        context = super(TomcatAppWarList, self).get_context_data(**kwargs)
        tomcat_app = get_object_or_404(TomcatApp, pk=self.args[0])
        context['tomcat_app'] = tomcat_app
        # context['tomcat_app_sql_count'] = TomcatAppSql.objects.filter(db__in=tomcat_app.tomcatappdb_set.all()).count()
        return context


@login_required
def active_war_package(request, pk):
    try:
        war = TomcatAppWar.objects.get(pk=pk)
    except TomcatAppWar.DoesNotExist:
        return JsonResponse({'msg': 'war does not exists'})
    war.tomcat_app.tomcatappwar_set.filter(active=True).update(active=False)
    war.active = True
    war.save()
    return JsonResponse({'msg': 0})


@login_required
def push_war_to_tomcat(request, tomcat_app_id, tomcat_app_node_id):
    try:
        tomcat_app = TomcatApp.objects.get(pk=tomcat_app_id)
    except TomcatApp.DoesNotExist:
        return JsonResponse({'msg': 'TomcatApp: %s does not exists!' % tomcat_app_id})
    try:
        tomcat_app_node = TomcatAppNode.objects.get(pk=tomcat_app_node_id)
    except TomcatAppNode.DoesNotExist:
        return JsonResponse({'msg': 'TomcatAppNode: %s does not exists!' % tomcat_app_node_id})

    if not tomcat_app_node.war_dir:
        return JsonResponse({'msg': '推送的节点没有配置war要放置的目录!'})

    active_war = tomcat_app.get_active_war()
    if not active_war:
        return JsonResponse({'msg': '没有激活的war包'})
    if not request.user.has_perm('services.push_war_pkg', active_war.tomcat_app.cluster):
        return JsonResponse({'msg': '你无权操作此项'})
    if not active_war.is_ready:
        return JsonResponse({'msg': 'Marmot正在下载地址中的War包, 请稍等!'})
    try:
        ret = tomcat_app.push_war(active_war, tomcat_app_node)
    except (IOError, xmlrpclib.Fault, httplib.BadStatusLine) as e:
        return JsonResponse({'msg': unicode(e)})
    if not ret:
        return JsonResponse({'msg': '添加任务失败！'})
    return JsonResponse({
        'msg': 0,
        'redirect': reverse('node_task_log_view', args=[active_war.tomcat_app.hex_identifier])
    })


class TomcatAppStaticCreate(PermissionRequiredMixin, CreateView):
    model = TomcatAppStatic
    form_class = TomcatAppStaticForm
    template_name = 'services/tomcat_app_static_form.html'
    success_url = 'tomcat_app_static_list'
    permission_required = 'services.add_tomcatappstatic'

    def get_success_url(self):
        return reverse(self.success_url, args=[self.object.tomcat_app.id])

    def get_initial(self):
        initial = super(TomcatAppStaticCreate, self).get_initial()
        self.tomcat_app = get_object_or_404(TomcatApp, pk=self.args[0])
        initial['tomcat_app'] = self.tomcat_app
        initial['active'] = True
        initial['user'] = self.request.user  # 这是为了初始化form中的user字段
        return initial

    def get_context_data(self, **kwargs):
        context = super(TomcatAppStaticCreate, self).get_context_data(**kwargs)
        context['tomcat_app'] = self.tomcat_app
        return context

    def inactive_set(self):
        """将前面处于激活状态的关闭"""
        self.tomcat_app.tomcatappstatic_set.filter(active=True).update(active=False)

    def form_valid(self, form):
        self.inactive_set()
        return super(TomcatAppStaticCreate, self).form_valid(form)


class TomcatAppStaticUpdate(PermissionRequiredMixin, UpdateView):
    model = TomcatAppStatic
    form_class = TomcatAppStaticForm
    context_object_name = 'tomcat_app_static'
    template_name = 'services/tomcat_app_static_form.html'
    success_url = 'tomcat_app_static_list'
    permission_required = 'services.change_tomcatappstatic'

    def get_initial(self):
        initial = super(TomcatAppStaticUpdate, self).get_initial()
        initial['user'] = self.request.user
        return initial

    def get_success_url(self):
        return reverse(self.success_url, args=[self.object.tomcat_app.id])

    def get_context_data(self, **kwargs):
        context = super(TomcatAppStaticUpdate, self).get_context_data(**kwargs)
        context['tomcat_app'] = self.object.tomcat_app
        return context


class TomcatAppStaticDelete(PermissionRequiredMixin, DeleteView):
    model = TomcatAppStatic
    context_object_name = 'tomcat_app_static'
    template_name = 'services/tomcat_app_static_confirm_delete.html'
    success_url = 'tomcat_app_static_list'
    permission_required = 'services.delete_tomcatappstatic'

    def get_success_url(self):
        return reverse(self.success_url, args=[self.object.tomcat_app.id])

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.active:
            # 如果任务在激活状态, 则不能删除
            self.object.delete()
        return HttpResponseRedirect(self.get_success_url())


class TomcatAppStaticList(TomcatAppWarList):
    model = TomcatAppStatic
    paginate_by = 10
    template_name = 'services/tomcat_app_static_list.html'


@login_required
def active_static_package(request, pk):
    try:
        pkg = TomcatAppStatic.objects.get(pk=pk)
    except TomcatAppStatic.DoesNotExist:
        return JsonResponse({'msg': 'static package does not exists'})
    pkg.tomcat_app.tomcatappstatic_set.filter(active=True).update(active=False)
    pkg.active = True
    pkg.save()
    return JsonResponse({'msg': 0})


@login_required
def push_static_to_web_html(request, tomcat_app_id, tomcat_app_node_id):
    try:
        tomcat_app = TomcatApp.objects.get(pk=tomcat_app_id)
    except TomcatApp.DoesNotExist:
        return JsonResponse({'msg': 'TomcatApp: %s does not exists!' % tomcat_app_id})
    try:
        tomcat_app_node = TomcatAppNode.objects.get(pk=tomcat_app_node_id)
    except TomcatAppNode.DoesNotExist:
        return JsonResponse({'msg': 'TomcatAppNode: %s does not exists!' % tomcat_app_node_id})

    if not tomcat_app_node.server.static_dir:
        return JsonResponse({'msg': '推送的节点没有配置静态文件要放置的目录!'})

    active_static = tomcat_app.get_active_static()
    if not active_static:
        return JsonResponse({'msg': '没有激活的static包'})

    if not request.user.has_perm('services.push_static_pkg', active_static.tomcat_app.cluster):
        return JsonResponse({'msg': '你无权操作此项'})

    try:
        ret = tomcat_app.push_static(active_static, tomcat_app_node)
    except (IOError, xmlrpclib.Fault, httplib.BadStatusLine) as e:
        return JsonResponse({'msg': unicode(e)})
    if not ret:
        return JsonResponse({'msg': '添加任务失败！'})
    return JsonResponse({
        'msg': 0,
        'redirect': reverse('node_task_log_view', args=[active_static.tomcat_app.hex_identifier])
    })


class TomcatAppSqlCreate(PermissionRequiredMixin, CreateView):
    model = TomcatAppSql
    form_class = TomcatAppSqlForm
    template_name = 'services/tomcat_app_sql_form.html'
    success_url = 'tomcat_app_sql_list'
    permission_required = 'services.add_tomcatappsql'

    def get_form(self, form_class=None):
        form = super(TomcatAppSqlCreate, self).get_form(form_class=form_class)
        form.fields['db'].queryset = form.fields['db'].queryset.filter(app=TomcatApp.objects.get(pk=self.args[0])).all()
        return form

    def get_success_url(self):
        return reverse(self.success_url, args=[self.object.tomcat_app.id])

    def get_initial(self):
        initial = super(TomcatAppSqlCreate, self).get_initial()
        self.tomcat_app = TomcatApp.objects.get(pk=self.args[0])
        initial['tomcat_app'] = self.tomcat_app
        initial['active'] = True
        initial['user'] = self.request.user  # 这是为了初始化form中的user字段
        return initial

    def get_context_data(self, **kwargs):
        context = super(TomcatAppSqlCreate, self).get_context_data(**kwargs)
        context['tomcat_app'] = self.tomcat_app
        return context


class TomcatAppSqlUpdate(PermissionRequiredMixin, UpdateView):
    model = TomcatAppSql
    form_class = TomcatAppSqlForm
    context_object_name = 'tomcat_app_sql'
    template_name = 'services/tomcat_app_sql_form.html'
    success_url = 'tomcat_app_sql_list'
    permission_required = 'services.change_tomcatappsql'
    dirty_state = [2]

    def get_initial(self):
        initial = super(TomcatAppSqlUpdate, self).get_initial()
        initial['user'] = self.request.user
        return initial

    def get_success_url(self):
        return reverse(self.success_url, args=[self.object.tomcat_app.id])

    def get_context_data(self, **kwargs):
        context = super(TomcatAppSqlUpdate, self).get_context_data(**kwargs)
        context['tomcat_app'] = self.object.tomcat_app
        return context

    def form_valid(self, form):
        if self.object.state not in self.dirty_state:
            return super(TomcatAppSqlUpdate, self).form_valid(form)
        else:
            return HttpResponseRedirect(self.get_success_url())


class TomcatAppSqlDelete(PermissionRequiredMixin, DeleteView):
    model = TomcatAppSql
    context_object_name = 'tomcat_app_sql'
    template_name = 'services/tomcat_app_sql_confirm_delete.html'
    success_url = 'tomcat_app_sql_list'
    permission_required = 'services.delete_tomcatappsql'
    dirty_state = [2]

    def get_success_url(self):
        return reverse(self.success_url, args=[self.object.tomcat_app.id])

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.state not in self.dirty_state:
            # 如果任务正在celery中执行, 则不能删除
            self.object.delete()
        return HttpResponseRedirect(self.get_success_url())


class TomcatAppSqlList(TomcatAppWarList):
    model = TomcatAppSql
    paginate_by = 10
    template_name = 'services/tomcat_app_sql_list.html'


@login_required
def execute_sql(request, pk):
    try:
        sql = TomcatAppSql.objects.get(pk=pk)
    except TomcatAppSql.DoesNotExist:
        return JsonResponse({'msg': 'TomcatAppSql: %s done not exists!' % pk})
    if not sql.db.is_ready:
        return JsonResponse({'msg': '对应数据库正在备份或执行SQL, 请稍等！'})
    if not sql.is_ready:
        return JsonResponse({'msg': '此sql正在执行队列中!'})
    if not request.user.has_perm('services.operate_db', sql.tomcat_app.cluster):
        return JsonResponse({'msg': '你无权操作此项'})
    if not os.path.isfile(sql.sql.path):
        return JsonResponse({'msg': 'sql文件: %s 不存在!' % sql.sql.name})
    sql.state = 2  # 标记该sql正在执行
    sql.save()
    db = sql.db
    db.state = 3  # 正在执行sql
    db.save()
    try:
        task_execute_sql.delay(sql.id)
    except redis.ConnectionError:
        sql.state = 1  # 空闲
        sql.save()
        db.state = 1  # 空闲
        db.save()
        return JsonResponse({'msg': 'Redis-ConnectionError'})
    return JsonResponse({'msg': 0})


class TomcatAppDBCreate(PermissionRequiredMixin, CreateView):
    model = TomcatAppDB
    form_class = TomcatAppDBForm
    template_name = 'services/tomcat_app_db_form.html'
    permission_required = 'services.add_tomcatappdb'

    def get_success_url(self):
        return self.tomcat_app.get_absolute_url()

    def get_initial(self):
        initial = super(TomcatAppDBCreate, self).get_initial()
        self.tomcat_app = get_object_or_404(TomcatApp, pk=self.args[0])
        initial['app'] = self.tomcat_app
        return initial

    def get_context_data(self, **kwargs):
        context = super(TomcatAppDBCreate, self).get_context_data(**kwargs)
        context['tomcat_app'] = self.tomcat_app
        return context


class TomcatAppDBUpdate(PermissionRequiredMixin, UpdateView):
    model = TomcatAppDB
    form_class = TomcatAppDBForm
    context_object_name = 'tomcat_app_db'
    template_name = 'services/tomcat_app_db_form.html'
    permission_required = 'services.change_tomcatappdb'


class TomcatAppDBDetail(LoginRequiredMixin, DetailView):
    model = TomcatAppDB
    context_object_name = 'tomcat_app_db'
    template_name = 'services/tomcat_app_db_detail.html'


class TomcatAppDBDelete(PermissionRequiredMixin, DeleteView):
    model = TomcatAppDB
    context_object_name = 'tomcat_app_db'
    template_name = 'services/tomcat_app_db_confirm_delete.html'
    permission_required = 'services.delete_tomcatappdb'
    dirty_state = [2, 3]

    def get_success_url(self):
        return self.object.app.get_absolute_url()
