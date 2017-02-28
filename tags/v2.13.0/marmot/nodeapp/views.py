# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import uuid
import redis

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, ListView, UpdateView, DetailView, DeleteView
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import JsonResponse
from django.conf import settings

from utils.mixins import LoginRequiredMixin, PermissionRequiredMixin

from .models import NodeApp, NodeSrcPkg
from .forms import NodeAppCreateForm, NodeAppEditForm, NodeSrcPkgForm


RDS = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)


class NodeAppCreate(PermissionRequiredMixin, CreateView):
    model = NodeApp
    form_class = NodeAppCreateForm
    template_name = 'nodeapp/nodeapp_form.html'
    success_url = reverse_lazy('node_app_list')
    permission_required = 'nodeapp.add_nodeapp'

    def get_initial(self):
        initial = super(NodeAppCreate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class NodeAppUpdate(PermissionRequiredMixin, UpdateView):
    model = NodeApp
    form_class = NodeAppEditForm
    context_object_name = 'nodeapp'
    template_name = 'nodeapp/nodeapp_form.html'
    permission_required = 'nodeapp.change_nodeapp'


class NodeAppDetail(LoginRequiredMixin, DetailView):
    model = NodeApp
    context_object_name = 'nodeapp'
    template_name = 'nodeapp/nodeapp_detail.html'

    def get_context_data(self, **kwargs):
        context = super(NodeAppDetail, self).get_context_data(**kwargs)
        context['is_alive'] = self.object.is_alive()
        return context


class NodeAppDelete(PermissionRequiredMixin, DeleteView):
    model = NodeApp
    context_object_name = 'nodeapp'
    template_name = 'nodeapp/nodeapp_confirm_delete.html'
    success_url = reverse_lazy('node_app_list')
    permission_required = 'nodeapp.delete_nodeapp'


class NodeAppList(LoginRequiredMixin, ListView):
    model = NodeApp
    paginate_by = 20
    context_object_name = 'nodeapp_list'
    template_name = 'nodeapp/nodeapp_list.html'

    def get_queryset(self):
        queryset = super(NodeAppList, self).get_queryset()
        user = self.request.user
        if user.profile.role.alias == 'developer' and user.profile.privilege < 3:
            queryset = queryset.filter(created_by=user)
        return queryset


class NodeSrcPkgCreate(PermissionRequiredMixin, CreateView):
    model = NodeSrcPkg
    form_class = NodeSrcPkgForm
    template_name = 'nodeapp/node_src_pkg_form.html'
    success_url = 'node_src_pkg_list'
    permission_required = 'nodeapp.add_nodesrcpkg'

    def get_success_url(self):
        return reverse(self.success_url, kwargs={'pk': self.object.app.id})

    def get_initial(self):
        initial = super(NodeSrcPkgCreate, self).get_initial()
        initial['created_by'] = self.request.user
        self.nodeapp = get_object_or_404(NodeApp, pk=self.kwargs['pk'])
        initial['app'] = self.nodeapp
        return initial

    def get_context_data(self, **kwargs):
        context = super(NodeSrcPkgCreate, self).get_context_data(**kwargs)
        context['node_app'] = self.nodeapp
        return context


class NodeSrcPkgDetail(LoginRequiredMixin, DetailView):
    model = NodeSrcPkg
    context_object_name = 'node_src_pkg'
    template_name = 'nodeapp/node_src_pkg_detail.html'


class NodeSrcPkgDelete(PermissionRequiredMixin, DeleteView):
    model = NodeSrcPkg
    context_object_name = 'node_src_pkg'
    template_name = 'nodeapp/node_src_pkg_confirm_delete.html'
    success_url = 'node_src_pkg_list'
    permission_required = 'nodeapp.delete_nodesrcpkg'

    def get_success_url(self):
        return reverse(self.success_url, kwargs={'pk': self.object.app.id})


class NodeSrcPkgList(LoginRequiredMixin, ListView):
    model = NodeSrcPkg
    paginate_by = 20
    context_object_name = 'node_src_pkg_list'
    template_name = 'nodeapp/node_src_pkg_list.html'

    def get_queryset(self):
        queryset = super(NodeSrcPkgList, self).get_queryset()
        queryset = queryset.filter(app__id=self.kwargs['pk'])
        return queryset

    def get_context_data(self, **kwargs):
        context = super(NodeSrcPkgList, self).get_context_data(**kwargs)
        node_app = get_object_or_404(NodeApp, pk=self.kwargs['pk'])
        context['node_app'] = node_app
        return context


@login_required
def start_node_app(request, pk):
    try:
        node_app = NodeApp.objects.get(id=pk)
    except NodeApp.DoesNotExist:
        return JsonResponse({'msg': 'NodeApp DoesNotExist'})

    if node_app.is_alive():
        return JsonResponse({'msg': 'NodeApp is alive'})

    stdout = node_app.startup()
    return JsonResponse({'msg': stdout})


@login_required
def kill_node_app(request, pk):
    try:
        node_app = NodeApp.objects.get(id=pk)
    except NodeApp.DoesNotExist:
        return JsonResponse({'msg': 'NodeApp DoesNotExist'})

    if not node_app.is_alive():
        return JsonResponse({'msg': 'NodeApp is not alive'})

    ret = node_app.kill()
    return JsonResponse({'msg': 0 if ret else 'error'})


@login_required
def push_node_src_pkg(request):
    ident = request.GET.get('ident')
    pkg_id = request.GET.get('pkgId')
    try:
        pkg = NodeSrcPkg.objects.get(id=pkg_id)
    except NodeSrcPkg.DoesNotExist:
        return JsonResponse({'msg': 'NodeSrcPkg DoesNotExist'})

    if pkg.push_to_server(ident):
        pkg.app.nodesrcpkg_set.filter(active=True).update(active=False)
        pkg.active = True
        pkg.save()
        return JsonResponse({'msg': 0})
    else:
        return JsonResponse({'msg': 'error'})


@login_required
def push_node_pkg_log(request):
    ident = request.GET.get('ident')
    if ident:
        return JsonResponse({'msg': [RDS.lpop(ident) for _ in xrange(RDS.llen(ident))]})
    else:
        return JsonResponse({'msg': ''})
