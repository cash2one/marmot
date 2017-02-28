# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import httplib
import xmlrpclib
import traceback
import time


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
                     StormCluster,StormNode,StormApp,StormAppJar,StormNodeJarDir,StormAppNode,
)

from .forms import  StormClusterForm,StormNodeForm,StormAppForm,StormAppJarForm,StormNodeJarDirForm,StormAppUpdateForm

class StormClusterList(LoginRequiredMixin, ListView):
    model = StormCluster
    context_object_name = 'storm_cluster_list'
    template_name = 'storm/storm_cluster_list.html'

class StormClusterCreate(PermissionRequiredMixin, CreateView):
    model = StormCluster
    form_class = StormClusterForm
    template_name = 'storm/storm_cluster_form.html'
    success_url = reverse_lazy('storm_cluster_list')
    permission_required = 'storm.add_stormcluster'
   


class StormClusterUpdate(PermissionRequiredMixin, UpdateView):
    model = StormCluster
    form_class = StormClusterForm
    context_object_name = 'storm_cluster'
    template_name = 'storm/storm_cluster_form.html'
    permission_required = 'storm.change_stormcluster'


class StormClusterDetail(LoginRequiredMixin, DetailView):
    model = StormCluster
    context_object_name = 'storm_cluster'
    template_name = 'storm/storm_cluster_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super(StormClusterDetail, self).get_context_data(**kwargs)
        user = self.request.user
        context['storm_node_list'] = self.object.stormnode_set.all()
        context['storm_app_list'] = self.object.stormapp_set.filter(user=user).all()
        return context
    

class StormClusterDelete(PermissionRequiredMixin, DeleteView):
    model = StormCluster
    context_object_name = 'storm_cluster'
    template_name = 'storm/storm_cluster_confirm_delete.html'
    success_url = reverse_lazy('storm_cluster_list')
    permission_required = 'storm.delete_stormcluster' 

class StormNodeList(LoginRequiredMixin, ListView):
    model = StormCluster
    context_object_name = 'storm_node_list'
    template_name = 'storm/storm_node_list.html'

class StormNodeCreate(PermissionRequiredMixin, CreateView):
    model = StormNode
    form_class = StormNodeForm
    context_object_name = 'storm_node'
    template_name = 'storm/storm_node_form.html'
    permission_required = 'storm.add_stormnode'
    
    def get_initial(self):
        initial = super(StormNodeCreate, self).get_initial()
        self.cluster = get_object_or_404(StormCluster, id=self.args[0])
        initial['cluster'] = self.cluster
        initial['user'] = self.request.user
        return initial
    
    def get_context_data(self, **kwargs):
        context = super(StormNodeCreate, self).get_context_data(**kwargs)
        context['cluster'] = self.cluster
        return context
    
    def get_success_url(self):
        return self.cluster.get_absolute_url()
    
    
class StormNodeUpdate(PermissionRequiredMixin, UpdateView):
    model = StormNode
    form_class = StormNodeForm
    context_object_name = 'storm_node'
    template_name = 'storm/storm_node_form.html'
    permission_required = 'storm.change_stormnode'
    

class StormNodeDetail(LoginRequiredMixin, DetailView):
    model = StormNode
    context_object_name = 'storm_node'
    template_name = 'storm/storm_node_detail.html'


class StormNodeDelete(PermissionRequiredMixin, DeleteView):
    model = StormNode
    context_object_name = 'storm_node'
    template_name = 'storm/storm_node_confirm_delete.html'
#     success_url = reverse_lazy('storm_node_list')
    permission_required = 'storm.delete_stormnode'     
    
    def get_success_url(self):
        return self.object.cluster.get_absolute_url()
    
class StormAppCreate(PermissionRequiredMixin, FormView):
    form_class = StormAppForm
    template_name = 'storm/storm_app_form.html'
    permission_required = 'storm.add_stormapp'
    
    def get_initial(self):
        initial = super(StormAppCreate, self).get_initial()
        self.cluster = get_object_or_404(StormCluster, id=self.args[0])
        initial['cluster'] = self.cluster
        initial['user'] = self.request.user
        return initial
    
    def get_form(self, form_class=None):
        form = super(StormAppCreate, self).get_form(form_class=form_class)
        form.fields['nodes'].queryset = self.cluster.stormnode_set.filter(type='nimbus')
        return form
    
    def get_context_data(self, **kwargs):
        context = super(StormAppCreate, self).get_context_data(**kwargs)
        context['cluster'] = self.cluster
        return context
    
    def get_success_url(self):
        return self.cluster.get_absolute_url()
    
    def form_valid(self, form):
        app = StormApp(
            cluster=form.cleaned_data['cluster'], 
            name=form.cleaned_data['name'],
            note=form.cleaned_data['note'],
            main_function = form.cleaned_data['main_function'],
            args = form.cleaned_data['args'],
        )
        try:
            app.save()
        except IntegrityError:
            form.add_error('name', '该Storm组下已经存在同名应用: %s' % form.cleaned_data['name'])
            return self.render_to_response(self.get_context_data(form=form))
        app.user.add(self.request.user)
        
        StormAppNode.objects.bulk_create(
            [StormAppNode(app=app, node=form.cleaned_data['nodes'])]
        )
        return super(StormAppCreate, self).form_valid(form)
    

class StormAppUpdate(PermissionRequiredMixin, FormView):
    form_class = StormAppUpdateForm
    template_name = 'storm/storm_app_form.html'
    permission_required = 'storm.change_stormapp'

    def get_initial(self):
        initial = super(StormAppUpdate, self).get_initial()
        self.object = get_object_or_404(StormApp, pk=self.kwargs['pk'])
        initial['cluster'] = self.object.cluster
        initial['name'] = self.object.name
        initial['note'] = self.object.note
        initial['main_function'] = self.object.main_function
        initial['args'] = self.object.args
        initial['nodes'] = [node.node for node in self.object.stormappnode_set.all()]
        initial['user'] = self.object.user.all()
        return initial

    def get_form(self, form_class=None):
        form = super(StormAppUpdate, self).get_form(form_class=form_class)
        form.fields['nodes'].queryset = self.object.cluster.stormnode_set.filter(type='nimbus')
        return form

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super(StormAppUpdate, self).get_context_data(**kwargs)
        context['storm_app'] = self.object
        return context

    def form_valid(self, form):
        if form.has_changed():
            self.object.name = form.cleaned_data['name']
            self.object.note = form.cleaned_data['note']
            self.object.main_function = form.cleaned_data['main_function']
            self.object.args = form.cleaned_data['args']
            try:
                self.object.save()
            except IntegrityError:
                form.add_error('name', '该Storm组下已经存在同名应用: %s' % form.cleaned_data['name'])
                return self.render_to_response(self.get_context_data(form=form))

            self.object.user.clear()
            self.object.user.add(*form.cleaned_data['user'])
            old_servers = [node.node for node in self.object.stormappnode_set.all()]
            now_server = form.cleaned_data['nodes']
            for node in self.object.stormappnode_set.all():
                if node.node != now_server:
                    node.delete()
            new_servers = []
            if now_server not in old_servers:
                new_servers.append(now_server)
            print new_servers
            new_app_node = [StormAppNode(app=self.object, node=node) for node in new_servers]
            if new_app_node:
                StormAppNode.objects.bulk_create(new_app_node)
        return super(StormAppUpdate, self).form_valid(form)
    
    
    
class StormAppDetail(LoginRequiredMixin, DetailView):
    model = StormApp
    context_object_name = 'storm_app'
    template_name = 'storm/storm_app_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super(StormAppDetail, self).get_context_data(**kwargs)
        context['nodes'] = self.object.stormappnode_set.all()
        context['active_jar'] = self.object.stormappjar_set.filter(active=True).first()
        return context
        

class StormAppDelete(PermissionRequiredMixin, DeleteView):
    model = StormApp
    context_object_name = 'storm_app'
    template_name = 'storm/storm_app_confirm_delete.html'
    permission_required = 'storm.delete_stormapp'

    def get_success_url(self):
        return self.object.cluster.get_absolute_url()
    

class StormAppList(LoginRequiredMixin, ListView):
    model = StormApp
    context_object_name = 'storm_app_list'
    template_name = 'storm/storm_app_list.html'
    

class StormAppJarCreate(PermissionRequiredMixin, CreateView):
    model = StormAppJar
    form_class = StormAppJarForm
    template_name = 'storm/storm_app_jar_form.html'
    success_url = 'storm_app_jar_list'
    permission_required = 'storm.add_stormappjar'

    def get_success_url(self):
        return reverse(self.success_url, args=[self.object.storm_app.id])

    def get_initial(self):
        initial = super(StormAppJarCreate, self).get_initial()
        self.storm_app = StormApp.objects.get(pk=self.args[0])
        initial['storm_app'] = self.storm_app
        initial['active'] = True
        initial['user'] = self.request.user  # 这是为了初始化form中的user字段
        return initial

    def get_context_data(self, **kwargs):
        context = super(StormAppJarCreate, self).get_context_data(**kwargs)
        context['storm_app'] = self.storm_app
        return context

    def inactive_set(self):
        """将前面处于激活状态的关闭"""
        self.storm_app.stormappjar_set.filter(active=True).update(active=False)

    def form_valid(self, form):
        self.inactive_set()
        return super(StormAppJarCreate, self).form_valid(form)

class StormAppJarUpdate(PermissionRequiredMixin, UpdateView):
    model = StormAppJar
    form_class = StormAppJarForm
    context_object_name = 'storm_app_jar'
    template_name = 'storm/storm_app_jar_form.html'
    success_url = 'storm_app_jar_list'
    permission_required = 'storm.change_stormappjar'
    dirty_state = [1]

    def get_initial(self):
        initial = super(StormAppJarUpdate, self).get_initial()
        initial['user'] = self.request.user
        return initial

    def get_success_url(self):
        return reverse(self.success_url, args=[self.object.storm_app.id])

    def get_context_data(self, **kwargs):
        context = super(StormAppJarUpdate, self).get_context_data(**kwargs)
        context['storm_app'] = self.object.storm_app
        return context

    def form_valid(self, form):
        if self.object.state not in self.dirty_state:
            return super(StormAppJarUpdate, self).form_valid(form)
        else:
            return HttpResponseRedirect(self.get_success_url())

class StormAppJarDelete(PermissionRequiredMixin, DeleteView):
    model = StormAppJar
    context_object_name = 'storm_app_jar'
    template_name = 'storm/storm_app_jar_confirm_delete.html'
    success_url = 'storm_app_jar_list'
    permission_required = 'storm.delete_stormappjar'
    dirty_state = [1]  # 处在这个状态不允许删除

    def get_success_url(self):
        return reverse(self.success_url, args=[self.object.storm_app.id])

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.state not in self.dirty_state and not self.object.active:
            # 如果任务正在celery中执行或激活状态, 则不能删除
            self.object.delete()
        return HttpResponseRedirect(self.get_success_url())


class StormAppJarList(LoginRequiredMixin, ListView):
    model = StormAppJar
    paginate_by = 10
    template_name = 'storm/storm_app_jar_list.html'

    def get_queryset(self):
        queryset = super(StormAppJarList, self).get_queryset()
        queryset = queryset.filter(storm_app__id=self.args[0])
        return queryset.order_by('-create_time')

    def get_context_data(self, **kwargs):
        context = super(StormAppJarList, self).get_context_data(**kwargs)
        storm_app = get_object_or_404(StormApp, pk=self.args[0])
        context['storm_app'] = storm_app
        return context

@login_required
def storm_node_switch(request, pk):
    try:
        ts = StormNode.objects.get(pk=pk)
    except StormNode.DoesNotExist:
        return JsonResponse({'msg': 'StormNode does not exists'})
    state = request.GET.get('state')
    if state not in ('start', 'stop'):
        return JsonResponse({'msg': 'State ValueError'})
#     if not request.user.has_perm('storm.operate_storm', ts.cluster):
#         return JsonResponse({'msg': '你无权操作此项'})
    if state == 'start':
        ret = ts.start()
        if ret:
            for i in range(20):
                time.sleep(1)
                if ts.is_alive():
                    break
    else:
        ret = ts.kill()
    if not ret:
        return JsonResponse({'msg': '%s storm-node error' % state})
    return JsonResponse({'msg': 0})

@login_required
def push_jar_to_storm(request, storm_app_id, storm_app_node_id):
    try:
        storm_app = StormApp.objects.get(pk=storm_app_id)
    except StormApp.DoesNotExist:
        return JsonResponse({'msg': 'StormApp: %s does not exists!' % storm_app_id})
    try:
        storm_app_node = StormAppNode.objects.get(pk=storm_app_node_id)
    except StormAppNode.DoesNotExist:
        return JsonResponse({'msg': 'StormAppNode: %s does not exists!' % storm_app_node_id})

    if not storm_app_node.jar_dir:
        return JsonResponse({'msg': '推送的节点没有配置jar要放置的目录!'})

    active_jar = storm_app.get_active_jar()
    if not active_jar:
        return JsonResponse({'msg': '没有激活的jar包'})
    if not active_jar.is_ready:
        return JsonResponse({'msg': 'Marmot正在下载地址中的Jar包, 请稍等!'})
    try:
        ret = storm_app.push_jar(active_jar, storm_app_node)
    except (IOError, xmlrpclib.Fault, httplib.BadStatusLine) as e:
        traceback.print_exc()
        return JsonResponse({'msg': unicode(e)})
    if not ret:
        return JsonResponse({'msg': '添加任务失败！'})
    return JsonResponse({
        'msg': 0,
        'redirect': reverse('node_task_log_view', args=[active_jar.storm_app.hex_identifier])
    })
    
@login_required
def run_jar_to_storm(request, storm_app_id, storm_app_node_id):
    try:
        storm_app = StormApp.objects.get(pk=storm_app_id)
    except StormApp.DoesNotExist:
        return JsonResponse({'msg': 'StormApp: %s does not exists!' % storm_app_id})
    try:
        storm_app_node = StormAppNode.objects.get(pk=storm_app_node_id)
    except StormAppNode.DoesNotExist:
        return JsonResponse({'msg': 'StormAppNode: %s does not exists!' % storm_app_node_id})

    if not storm_app_node.jar_dir:
        return JsonResponse({'msg': '推送的节点没有配置jar要放置的目录!'})
    active_jar = storm_app.get_active_jar()
    if not active_jar:
        return JsonResponse({'msg': '没有激活的jar包'})
    if not active_jar.is_ready:
        return JsonResponse({'msg': 'Marmot正在下载地址中的Jar包, 请稍等!'})
    try:
        ret = storm_app.run_jar(active_jar, storm_app_node,storm_app)
    except (IOError, xmlrpclib.Fault, httplib.BadStatusLine) as e:
        traceback.print_exc()
        return JsonResponse({'msg': unicode(e)})
    if not ret:
        return JsonResponse({'msg': '添加任务失败！'})
    return JsonResponse({
        'msg': 0,
        'redirect': reverse('node_task_log_view', args=[active_jar.storm_app.hex_identifier])
    })
    

@login_required
def active_jar_package(request, pk):
    try:
        jar = StormAppJar.objects.get(pk=pk)
    except StormAppJar.DoesNotExist:
        return JsonResponse({'msg': 'war does not exists'})
    if not jar.is_ready:
        return JsonResponse({'msg': '不能激活此war包'})
    jar.storm_app.stormappjar_set.filter(active=True).update(active=False)
    jar.active = True
    jar.save()
    return JsonResponse({'msg': 0})

class StormNodeJarDirCreate(PermissionRequiredMixin, CreateView):
    model = StormNodeJarDir
    form_class = StormNodeJarDirForm
    template_name = 'storm/storm_node_jar_dir_form.html'
    permission_required = 'storm.add_stormnodejardir'

    def get_initial(self):
        initial = super(StormNodeJarDirCreate, self).get_initial()
        self.storm_node = StormNode.objects.get(pk=self.args[0])
        initial['storm_node'] = self.storm_node
        return initial

    def get_success_url(self):
        return reverse('storm_node_detail', kwargs={'pk': self.args[0]})

    def get_context_data(self, **kwargs):
        context = super(StormNodeJarDirCreate, self).get_context_data(**kwargs)
        context['storm_node'] = self.storm_node
        return context


class StormNodeJarDirUpdate(PermissionRequiredMixin, UpdateView):
    model = StormNodeJarDir
    form_class = StormNodeJarDirForm
    context_object_name = 'storm_node_jar_dir'
    template_name = 'storm/storm_node_jar_dir_form.html'
    permission_required = 'storm.change_stormnodejardir'

    def get_success_url(self):
        return self.object.storm_node.get_absolute_url()


class StormNodeJarDirDelete(PermissionRequiredMixin, DeleteView):
    model = StormNodeJarDir
    context_object_name = 'storm_node_jar_dir'
    template_name = 'storm/storm_node_jar_dir_confirm_delete.html'
    permission_required = 'storm.delete_stormnodejardir'

    def get_success_url(self):
        return self.object.storm_node.get_absolute_url()


@login_required
def config_storm_app_node_jar_dir(request):
    storm_app_node_id = request.GET.get('nid')
    jar_dir_id = request.GET.get('wid')
    if jar_dir_id is None or storm_app_node_id is None:
        return JsonResponse({'msg': 'ValueError'})
    try:
        ts_jar_dir = StormNodeJarDir.objects.get(id=jar_dir_id)
    except StormNodeJarDir.DoesNotExist:
        return JsonResponse({'msg': 'StormNodeJarDir: %s does not exist' % ts_jar_dir})
    try:
        tomcat_app_node = StormAppNode.objects.get(id=storm_app_node_id)
    except StormAppNode.DoesNotExist:
        return JsonResponse({'msg': 'StormAppNode: %s does not exist' % storm_app_node_id})
    tomcat_app_node.jar_dir = ts_jar_dir
    tomcat_app_node.save()
    return JsonResponse({'msg': 0})


@login_required
def get_storm_node_jar_dir(request, nid):
    try:
        storm_app_node = StormAppNode.objects.get(id=nid)
    except StormAppNode.DoesNotExist:
        return JsonResponse({'msg': 'StormAppNode: %s does not exist' % nid})
    tsw_list = storm_app_node.node.stormnodejardir_set.all()
    return JsonResponse({
        'msg': 0, 'nid': nid,
        'data': [{'tswid': tsw.id, 'wdir': tsw.jar_dir} for tsw in tsw_list]
    })
