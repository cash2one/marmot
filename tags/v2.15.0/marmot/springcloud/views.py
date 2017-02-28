# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import json
import logging
import httplib
import xmlrpclib
import redis

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, ListView, UpdateView, DetailView, DeleteView
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse_lazy
from django.http import JsonResponse, HttpResponseNotFound
from django.conf import settings

from utils.mixins import LoginRequiredMixin, PermissionRequiredMixin
from utils.node_proxy import NodeProxy

from .models import (
    SpringCloudCluster, SpringCloudNode,
    SpringCloudApp, SpringCloudFile, SpringCloudBackup,
)
from .forms import (
    SpringCloudClusterForm, SpringCloudNodeForm,
    SpringCloudAppForm, SpringCloudFileForm
)

logger = logging.getLogger('marmot')

RDS = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)


class SpringCloudClusterCreate(PermissionRequiredMixin, CreateView):
    model = SpringCloudCluster
    form_class = SpringCloudClusterForm
    template_name = 'springcloud/springcloud_cluster_form.html'
    success_url = reverse_lazy('springcloud_cluster_list')
    permission_required = 'springcloud.add_springcloudcluster'

    def get_initial(self):
        initial = super(SpringCloudClusterCreate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class SpringCloudClusterUpdate(PermissionRequiredMixin, UpdateView):
    model = SpringCloudCluster
    form_class = SpringCloudClusterForm
    context_object_name = 'springcloud_cluster'
    template_name = 'springcloud/springcloud_cluster_form.html'
    permission_required = 'springcloud.change_springcloudcluster'


class SpringCloudClusterDetail(LoginRequiredMixin, DetailView):
    model = SpringCloudCluster
    context_object_name = 'springcloud_cluster'
    template_name = 'springcloud/springcloud_cluster_detail.html'

    def get_context_data(self, **kwargs):
        context = super(SpringCloudClusterDetail, self).get_context_data(**kwargs)
        user = self.request.user
        springcloud_app_list = self.object.springcloudapp_set.all()
        if user.profile.role.alias == 'developer' and user.profile.privilege < 3:
            springcloud_app_list = springcloud_app_list.filter(develops=user)
        context['springcloud_app_list'] = springcloud_app_list
        context['springcloud_node_list'] = self.object.springcloudnode_set.all()
        return context


class SpringCloudClusterDelete(PermissionRequiredMixin, DeleteView):
    model = SpringCloudCluster
    context_object_name = 'springcloud_cluster'
    template_name = 'springcloud/springcloud_cluster_confirm_delete.html'
    success_url = reverse_lazy('springcloud_cluster_list')
    permission_required = 'springcloud.delete_springcloudcluster'


class SpringCloudClusterList(LoginRequiredMixin, ListView):
    model = SpringCloudCluster
    paginate_by = 20
    context_object_name = 'springcloud_cluster_list'
    template_name = 'springcloud/springcloud_cluster_list.html'


class SpringCloudNodeCreate(PermissionRequiredMixin, CreateView):
    model = SpringCloudNode
    form_class = SpringCloudNodeForm
    template_name = 'springcloud/springcloud_node_form.html'
    permission_required = 'springcloud.add_springcloudnode'

    def get_initial(self):
        initial = super(SpringCloudNodeCreate, self).get_initial()
        self.cluster = get_object_or_404(SpringCloudCluster, pk=self.kwargs['pk'])
        initial['cluster'] = self.cluster
        initial['created_by'] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super(SpringCloudNodeCreate, self).get_context_data(**kwargs)
        context['cluster'] = self.cluster
        return context

    def get_success_url(self):
        return self.object.cluster.get_absolute_url()


class SpringCloudNodeUpdate(PermissionRequiredMixin, UpdateView):
    model = SpringCloudNode
    form_class = SpringCloudNodeForm
    context_object_name = 'springcloud_node'
    template_name = 'springcloud/springcloud_node_form.html'
    permission_required = 'springcloud.change_springcloudnode'

    def get_context_data(self, **kwargs):
        context = super(SpringCloudNodeUpdate, self).get_context_data(**kwargs)
        context['cluster'] = self.object.cluster
        return context


class SpringCloudNodeDetail(LoginRequiredMixin, DetailView):
    model = SpringCloudNode
    context_object_name = 'springcloud_node'
    template_name = 'springcloud/springcloud_node_detail.html'


class SpringCloudNodeDelete(PermissionRequiredMixin, DeleteView):
    model = SpringCloudNode
    context_object_name = 'springcloud_node'
    template_name = 'springcloud/springcloud_node_confirm_delete.html'
    permission_required = 'springcloud.delete_springcloudnode'

    def get_success_url(self):
        return self.object.cluster.get_absolute_url()


class SpringCloudAppCreate(PermissionRequiredMixin, CreateView):
    model = SpringCloudApp
    form_class = SpringCloudAppForm
    template_name = 'springcloud/springcloud_app_form.html'
    permission_required = 'springcloud.add_springcloudapp'

    def get_initial(self):
        initial = super(SpringCloudAppCreate, self).get_initial()
        self.cluster = get_object_or_404(SpringCloudCluster, pk=self.kwargs['pk'])
        initial['cluster'] = self.cluster
        initial['created_by'] = self.request.user
        return initial

    def get_form(self, form_class=None):
        form = super(SpringCloudAppCreate, self).get_form(form_class=form_class)
        form.fields['nodes'].queryset = self.cluster.springcloudnode_set.all()
        return form

    def get_context_data(self, **kwargs):
        context = super(SpringCloudAppCreate, self).get_context_data(**kwargs)
        context['cluster'] = self.cluster
        return context

    def get_success_url(self):
        return self.object.cluster.get_absolute_url()


class SpringCloudAppUpdate(PermissionRequiredMixin, UpdateView):
    model = SpringCloudApp
    form_class = SpringCloudAppForm
    context_object_name = 'springcloud_app'
    template_name = 'springcloud/springcloud_app_form.html'
    permission_required = 'springcloud.change_springcloudapp'

    def get_form(self, form_class=None):
        form = super(SpringCloudAppUpdate, self).get_form(form_class=form_class)
        form.fields['nodes'].queryset = self.object.cluster.springcloudnode_set.all()
        return form

    def get_context_data(self, **kwargs):
        context = super(SpringCloudAppUpdate, self).get_context_data(**kwargs)
        context['cluster'] = self.object.cluster
        return context


class SpringCloudAppDetail(LoginRequiredMixin, DetailView):
    model = SpringCloudApp
    context_object_name = 'springcloud_app'
    template_name = 'springcloud/springcloud_app_detail.html'

    def get_context_data(self, **kwargs):
        context = super(SpringCloudAppDetail, self).get_context_data(**kwargs)
        context['lib_files_count'] = self.object.springcloudfile_set.filter(type=0).count()
        context['libs_files_count'] = self.object.springcloudfile_set.filter(type=1).count()
        context['config_files_count'] = self.object.springcloudfile_set.filter(type=2).count()
        context['backup_count'] = self.object.springcloudbackup_set.count()

        alive_apps = []
        for node in self.object.nodes.all():
            if self.object.is_alive(node):
                alive_apps.append(node.name)
        context['alive_apps'] = alive_apps
        return context


class SpringCloudAppDelete(PermissionRequiredMixin, DeleteView):
    model = SpringCloudApp
    context_object_name = 'springcloud_app'
    template_name = 'springcloud/springcloud_app_confirm_delete.html'
    permission_required = 'springcloud.delete_springcloudapp'

    def get_success_url(self):
        return self.object.cluster.get_absolute_url()


@login_required
def start_springcloud_app(request, app):
    node = request.GET.get('node')
    try:
        sca = SpringCloudApp.objects.get(pk=app)
    except SpringCloudApp.DoesNotExist as e:
        return JsonResponse({'msg': str(e)})

    try:
        sc_node = SpringCloudNode.objects.get(pk=node)
    except SpringCloudNode.DoesNotExist as e:
        return JsonResponse({'msg': str(e)})

    if not request.user.has_perm('springcloud.operate_springcloudapp', sca.cluster):
        return JsonResponse({'msg': '你无权操作此项'})

    ret = sca.start(sc_node)
    return JsonResponse({'msg': ret})


@login_required
def kill_springcloud_app(request, app):
    node = request.GET.get('node')
    try:
        sca = SpringCloudApp.objects.get(pk=app)
    except SpringCloudApp.DoesNotExist as e:
        return JsonResponse({'msg': str(e)})

    try:
        sc_node = SpringCloudNode.objects.get(pk=node)
    except SpringCloudNode.DoesNotExist as e:
        return JsonResponse({'msg': str(e)})

    if not request.user.has_perm('springcloud.operate_springcloudapp', sca.cluster):
        return JsonResponse({'msg': '你无权操作此项'})

    ret = sca.kill(sc_node)
    return JsonResponse({'msg': ret})


@login_required
def sync_springcloud_files(request, app):
    node = request.GET.get('node')
    ident = request.GET.get('ident')
    try:
        sca = SpringCloudApp.objects.get(pk=app)
    except SpringCloudApp.DoesNotExist as e:
        return JsonResponse({'msg': str(e)})

    try:
        sc_node = SpringCloudNode.objects.get(pk=node)
    except SpringCloudNode.DoesNotExist as e:
        return JsonResponse({'msg': str(e)})

    if not request.user.has_perm('springcloud.operate_springcloudapp', sca.cluster):
        return JsonResponse({'msg': '你无权操作此项'})

    stat, msg = sca.sync_files(sc_node, ident)
    return JsonResponse({'msg': 0 if stat else msg})


@login_required
def springcloud_file_upload(request, app=None, type=None):
    if request.method == 'POST':
        form = SpringCloudFileForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.save()
            data = {
                'is_valid': True,
                'name': unicode(f),
                'url': f.file.url,
                'created_by': f.created_by.get_full_name(),
                'create_time': f.create_time,
            }
        else:
            data = {'is_valid': False}
        return JsonResponse(data)
    else:
        return HttpResponseNotFound()


class SpringCloudFileList(LoginRequiredMixin, ListView):
    model = SpringCloudFile
    paginate_by = 20
    context_object_name = 'springcloud_file_list'
    template_name = 'springcloud/springcloud_file_list.html'

    def get_queryset(self):
        queryset = super(SpringCloudFileList, self).get_queryset()
        self.springcloud_app = get_object_or_404(SpringCloudApp, pk=self.kwargs['app'])
        queryset = queryset.filter(app=self.springcloud_app, type=self.kwargs['type'])
        return queryset

    def get_context_data(self, **kwargs):
        context = super(SpringCloudFileList, self).get_context_data(**kwargs)
        context['springcloud_app'] = self.springcloud_app
        context['type'] = self.kwargs['type']
        context['lib_files_count'] = self.springcloud_app.springcloudfile_set.filter(type=0).count()
        context['libs_files_count'] = self.springcloud_app.springcloudfile_set.filter(type=1).count()
        context['config_files_count'] = self.springcloud_app.springcloudfile_set.filter(type=2).count()
        context['backup_count'] = self.springcloud_app.springcloudbackup_set.count()
        return context


@login_required
def springcloud_file_delete(request):
    pk = request.GET.get('pk')
    try:
        scf = SpringCloudFile.objects.get(pk=pk)
    except SpringCloudFile.DoesNotExist as e:
        return JsonResponse({'msg': str(e)})

    if not request.user.has_perm('springcloud.delete_springcloudapp_files', scf.app.cluster):
        return JsonResponse({'msg': '你无权操作此项'})

    if scf.type == 0:
        rel_path = os.path.join('lib', unicode(scf))
    elif scf.type == 1:
        rel_path = os.path.join('lib', 'libs', unicode(scf))
    elif scf.type == 2:
        rel_path = os.path.join('config', unicode(scf))
    else:
        return JsonResponse({'msg': 'SpringCloudFile - type: %s ERROR!' % scf.type})

    # 删除各个节点上的文件
    error_list = []
    for node in scf.app.nodes.all():
        proxy = NodeProxy(node.server.ip, settings.NODE_PORT, timeout=5.0)
        try:
            stat, msg = proxy.remove(os.path.join(node.cwd, 'app', scf.app.name, rel_path))
            if not stat:
                error_list.append('%s - %s' % (node.server, unicode(msg, 'utf-8')))
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine) as e:
            error_list.append('%s - %s' % (node.server, str(e)))

    if error_list:
        return JsonResponse({'msg': '\n'.join(error_list)})

    scf.delete()

    return JsonResponse({'msg': 0})


class SpringCloudBackupList(LoginRequiredMixin, ListView):
    model = SpringCloudBackup
    paginate_by = 20
    context_object_name = 'springcloud_backup_list'
    template_name = 'springcloud/springcloud_backup_list.html'

    def get_queryset(self):
        queryset = super(SpringCloudBackupList, self).get_queryset()
        self.springcloud_app = get_object_or_404(SpringCloudApp, pk=self.kwargs['app'])
        queryset = queryset.filter(app=self.springcloud_app)
        if self.request.GET.get('node'):
            queryset = queryset.filter(node=self.request.GET.get('node'))
        return queryset

    def get_context_data(self, **kwargs):
        context = super(SpringCloudBackupList, self).get_context_data(**kwargs)
        context['springcloud_app'] = self.springcloud_app
        context['node'] = self.request.GET.get('node')
        context['lib_files_count'] = self.springcloud_app.springcloudfile_set.filter(type=0).count()
        context['libs_files_count'] = self.springcloud_app.springcloudfile_set.filter(type=1).count()
        context['config_files_count'] = self.springcloud_app.springcloudfile_set.filter(type=2).count()
        context['backup_count'] = self.springcloud_app.springcloudbackup_set.count()
        return context


@csrf_exempt
def springcloud_backup_create(request):
    try:
        data = json.loads(request.body)
    except ValueError:
        logger.error('SpringCloudBackup Error - body ValueError %s' % request.body)
        return JsonResponse({'msg':  1})

    appname = data.get('appname')
    path = data.get('path')
    hostname = data.get('hostname')

    try:
        app = SpringCloudApp.objects.get(name=appname)
    except SpringCloudApp.DoesNotExist:
        logger.error('SpringCloudBackup Error - SpringCloudApp: %s DoesNotExist' % appname)
        return JsonResponse({'msg':  1})

    try:
        node = SpringCloudNode.objects.get(server__hostname=hostname)
    except SpringCloudApp.DoesNotExist:
        logger.error('SpringCloudBackup Error - SpringCloudNode: Server[%s] DoesNotExist' % hostname)
        return JsonResponse({'msg':  1})

    scb = SpringCloudBackup(app=app, node=node, path=path)
    scb.save()

    return JsonResponse({'msg':  0})


@login_required
def springcloud_rollback(request):
    pk = request.GET.get('pk')
    ident = request.GET.get('ident')
    try:
        scb = SpringCloudBackup.objects.get(pk=pk)
    except SpringCloudBackup.DoesNotExist as e:
        return JsonResponse({'msg': str(e)})

    if not request.user.has_perm('springcloud.operate_springcloudapp', scb.app.cluster):
        return JsonResponse({'msg': '你无权操作此项'})

    if scb.rollback(ident) is True:
        return JsonResponse({'msg': 0})
    else:
        return JsonResponse({'msg': 'Rollback Error'})


@login_required
def springcloud_backup_delete(request):
    pk = request.GET.get('pk')
    try:
        scb = SpringCloudBackup.objects.get(pk=pk)
    except SpringCloudBackup.DoesNotExist as e:
        return JsonResponse({'msg': str(e)})

    if not request.user.has_perm('springcloud.delete_springcloudapp_files', scb.app.cluster):
        return JsonResponse({'msg': '你无权操作此项'})

    scb.delete()
    return JsonResponse({'msg': 0})


@login_required
def springcloud_backup_options(request):
    app = request.GET.get('app')
    node = request.GET.get('node')
    try:
        scb_list = SpringCloudBackup.objects.filter(app=app, node=node).all()
    except SpringCloudBackup.DoesNotExist as e:
        return JsonResponse({'msg': str(e)})

    return JsonResponse({'msg': 0, 'data': [{'id': scb.id, 'path': os.path.basename(scb.path)} for scb in scb_list]})
