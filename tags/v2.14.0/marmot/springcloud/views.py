# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import uuid
import redis

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, ListView, UpdateView, DetailView, DeleteView
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseNotFound
from django.conf import settings

from utils.mixins import LoginRequiredMixin, PermissionRequiredMixin

from .models import (
    SpringCloudCluster, SpringCloudNode,
    SpringCloudApp, SpringCloudFile,
    SpringCloudFileDeleteError, SpringCloudFileDeleteSuccess
)
from .forms import (
    SpringCloudClusterForm, SpringCloudNodeForm,
    SpringCloudAppForm, SpringCloudFileForm
)


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
        context['uuid4'] = uuid.uuid4().get_hex()

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
        return context


@login_required
def springcloud_file_delete(request):
    pk = request.GET.get('pk')

    if not request.user.has_perm('springcloud.delete_springcloudfile'):
        return JsonResponse({'msg': '你无权操作此项'})

    try:
        SpringCloudFile.objects.get(pk=pk).delete()
        return JsonResponse({'msg': 0})
    except SpringCloudFile.DoesNotExist as e:
        return JsonResponse({'msg': str(e)})
    except SpringCloudFileDeleteError as e:
        return JsonResponse({'msg': str(e)})
    except SpringCloudFileDeleteSuccess:
        return JsonResponse({'msg': 0})
