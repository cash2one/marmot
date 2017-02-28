# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import logging
import httplib
import xmlrpclib

import redis

from django.shortcuts import get_object_or_404
from django.views.generic import (
    TemplateView, CreateView, ListView,
    UpdateView, DetailView, DeleteView
)
from django.core.urlresolvers import reverse_lazy
from django.contrib import messages
from django.conf import settings

from utils.mixins import LoginRequiredMixin, PermissionRequiredMixin
from utils.node_proxy import NodeProxy

from .models import (
    RedisClusterMonitor, RedisNode,
    ESMonitor, Neo4jMonitor, HBaseClusterMonitor,
    ActiveMqMonitor, SpringCloudMonitor, KafkaMonitor
)
from .forms import (
    RedisClusterMonitorForm, RedisNodeForm,
    ESMonitorForm, Neo4jMonitorForm, HBaseClusterMonitorForm,
    ActiveMqMonitorForm, SpringCloudMonitorForm, KafkaMonitorForm
)


RDS = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)

logger = logging.getLogger('marmot')


# *******************************************************************************
# RedisClusterMonitor
# *******************************************************************************


class RedisClusterMonitorCreate(PermissionRequiredMixin, CreateView):
    model = RedisClusterMonitor
    form_class = RedisClusterMonitorForm
    template_name = 'monitor/redis_cluster_form.html'
    success_url = reverse_lazy('redis_cluster_list')
    permission_required = 'monitor.add_redisclustermonitor'

    def get_initial(self):
        initial = super(RedisClusterMonitorCreate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class RedisClusterMonitorUpdate(PermissionRequiredMixin, UpdateView):
    model = RedisClusterMonitor
    form_class = RedisClusterMonitorForm
    context_object_name = 'redis_cluster_monitor'
    template_name = 'monitor/redis_cluster_form.html'
    permission_required = 'monitor.change_redisclustermonitor'

    def get_initial(self):
        initial = super(RedisClusterMonitorUpdate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class RedisClusterMonitorDetail(LoginRequiredMixin, DetailView):
    model = RedisClusterMonitor
    context_object_name = 'redis_cluster_monitor'
    template_name = 'monitor/redis_cluster_detail.html'


class RedisClusterInfo(RedisClusterMonitorDetail):
    model = RedisClusterMonitor
    context_object_name = 'object'
    template_name = 'monitor/monitor_view.html'

    def get_context_data(self, **kwargs):
        context = super(RedisClusterInfo, self).get_context_data(**kwargs)
        context['title'] = 'Redis集群监控信息'
        context['monitor_info'] = json.dumps(self.object.get_info(), indent=4) + '\n\n' + \
                                  json.dumps(self.object.get_nodes(), indent=4)
        return context


class RedisClusterMonitorDelete(PermissionRequiredMixin, DeleteView):
    model = RedisClusterMonitor
    context_object_name = 'redis_cluster_monitor'
    template_name = 'monitor/redis_cluster_confirm_delete.html'
    success_url = reverse_lazy('redis_cluster_list')
    permission_required = 'monitor.delete_redisclustermonitor'


class RedisClusterMonitorList(LoginRequiredMixin, ListView):
    model = RedisClusterMonitor
    context_object_name = 'redis_cluster_list'
    template_name = 'monitor/redis_cluster_list.html'
    ordering = 'id'


class RedisNodeCreate(PermissionRequiredMixin, CreateView):
    model = RedisNode
    form_class = RedisNodeForm
    template_name = 'monitor/redis_node_form.html'
    permission_required = 'monitor.add_redisnode'

    def get_initial(self):
        initial = super(RedisNodeCreate, self).get_initial()
        self.cluster = get_object_or_404(RedisClusterMonitor, id=self.args[0])
        initial['cluster'] = self.cluster
        initial['created_by'] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super(RedisNodeCreate, self).get_context_data(**kwargs)
        context['cluster'] = self.cluster
        return context

    def get_success_url(self):
        return self.cluster.get_absolute_url()


class RedisNodeUpdate(PermissionRequiredMixin, UpdateView):
    model = RedisNode
    form_class = RedisNodeForm
    context_object_name = 'redis_node'
    template_name = 'monitor/redis_node_form.html'
    permission_required = 'monitor.change_redisnode'


class RedisNodeDetail(LoginRequiredMixin, DetailView):
    model = RedisNode
    context_object_name = 'redis_node'
    template_name = 'monitor/redis_node_detail.html'


class RedisNodeInfo(RedisNodeDetail):
    model = RedisNode
    context_object_name = 'object'
    template_name = 'monitor/monitor_view.html'

    def get_context_data(self, **kwargs):
        context = super(RedisNodeInfo, self).get_context_data(**kwargs)
        context['title'] = 'Redis监控信息'
        context['monitor_info'] = \
            '# Server\n' + json.dumps(self.object.get_info(section='Server'), indent=4) + \
            '\n# Clients\n' + json.dumps(self.object.get_info(section='Clients'), indent=4) + \
            '\n# Memory\n' + json.dumps(self.object.get_info(section='Memory'), indent=4) + \
            '\n# Persistence\n' + json.dumps(self.object.get_info(section='Persistence'), indent=4) + \
            '\n# Stats\n' + json.dumps(self.object.get_info(section='Stats'), indent=4) + \
            '\n# Replication\n' + json.dumps(self.object.get_info(section='Replication'), indent=4) + \
            '\n# CPU\n' + json.dumps(self.object.get_info(section='CPU'), indent=4) + \
            '\n# Cluster\n' + json.dumps(self.object.get_info(section='Cluster'), indent=4) + \
            '\n# Keyspace\n' + json.dumps(self.object.get_info(section='Keyspace'), indent=4)
        return context


class RedisNodeDelete(PermissionRequiredMixin, DeleteView):
    model = RedisNode
    context_object_name = 'redis_node'
    template_name = 'monitor/redis_node_confirm_delete.html'
    permission_required = 'monitor.delete_redisnode'

    def get_success_url(self):
        return self.object.cluster.get_absolute_url()


# *******************************************************************************
# HBaseClusterMonitor
# *******************************************************************************


class HBaseClusterMonitorCreate(PermissionRequiredMixin, CreateView):
    model = HBaseClusterMonitor
    form_class = HBaseClusterMonitorForm
    template_name = 'monitor/hbase_cluster_form.html'
    success_url = reverse_lazy('hbase_cluster_list')
    permission_required = 'monitor.add_hbaseclustermonitor'

    def get_initial(self):
        initial = super(HBaseClusterMonitorCreate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class HBaseClusterMonitorUpdate(PermissionRequiredMixin, UpdateView):
    model = HBaseClusterMonitor
    form_class = HBaseClusterMonitorForm
    context_object_name = 'hbase_cluster_monitor'
    template_name = 'monitor/hbase_cluster_form.html'
    permission_required = 'monitor.change_hbaseclustermonitor'

    def get_initial(self):
        initial = super(HBaseClusterMonitorUpdate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class HBaseClusterMonitorDetail(LoginRequiredMixin, DetailView):
    model = HBaseClusterMonitor
    context_object_name = 'hbase_cluster_monitor'
    template_name = 'monitor/hbase_cluster_detail.html'


class HBaseClusterMonitorInfo(HBaseClusterMonitorDetail):
    context_object_name = 'object'
    template_name = 'monitor/monitor_view.html'

    def get_context_data(self, **kwargs):
        context = super(HBaseClusterMonitorInfo, self).get_context_data(**kwargs)
        context['title'] = 'HBase集群监控信息'
        node = NodeProxy(self.object.host, settings.NODE_PORT)
        try:
            context['monitor_info'] = node.hbase_status_simple()
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            messages.error(self.request, "没连上主机: %s" % self.object.host)
            context['monitor_info'] = ''
        return context


class HBaseClusterMonitorDelete(PermissionRequiredMixin, DeleteView):
    model = HBaseClusterMonitor
    context_object_name = 'hbase_cluster_monitor'
    template_name = 'monitor/hbase_cluster_confirm_delete.html'
    success_url = reverse_lazy('hbase_cluster_list')
    permission_required = 'monitor.delete_hbaseclustermonitor'


class HBaseClusterMonitorList(LoginRequiredMixin, ListView):
    model = HBaseClusterMonitor
    context_object_name = 'hbase_cluster_monitor_list'
    template_name = 'monitor/hbase_cluster_list.html'
    ordering = 'id'


# *******************************************************************************
# ESMonitor
# *******************************************************************************


class ESMonitorCreate(PermissionRequiredMixin, CreateView):
    model = ESMonitor
    form_class = ESMonitorForm
    template_name = 'monitor/es_form.html'
    success_url = reverse_lazy('es_list')
    permission_required = 'monitor.add_esmonitor'

    def get_initial(self):
        initial = super(ESMonitorCreate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class ESMonitorUpdate(PermissionRequiredMixin, UpdateView):
    model = ESMonitor
    form_class = ESMonitorForm
    context_object_name = 'es_monitor'
    template_name = 'monitor/es_form.html'
    permission_required = 'monitor.change_esmonitor'

    def get_initial(self):
        initial = super(ESMonitorUpdate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class ESMonitorDetail(LoginRequiredMixin, DetailView):
    model = ESMonitor
    context_object_name = 'es_monitor'
    template_name = 'monitor/es_detail.html'


class ESMonitorInfo(ESMonitorDetail):
    context_object_name = 'object'
    template_name = 'monitor/monitor_view.html'

    def get_context_data(self, **kwargs):
        context = super(ESMonitorInfo, self).get_context_data(**kwargs)
        context['title'] = "ES监控信息"
        context['monitor_info'] = json.dumps(self.object.get_state(), indent=4)
        return context


class ESMonitorDelete(PermissionRequiredMixin, DeleteView):
    model = ESMonitor
    context_object_name = 'es_monitor'
    template_name = 'monitor/es_confirm_delete.html'
    success_url = reverse_lazy('es_list')
    permission_required = 'monitor.delete_esmonitor'


class ESMonitorList(LoginRequiredMixin, ListView):
    model = ESMonitor
    context_object_name = 'es_monitor_list'
    template_name = 'monitor/es_list.html'
    ordering = 'id'


# *******************************************************************************
# Neo4jMonitor
# *******************************************************************************


class Neo4jMonitorCreate(PermissionRequiredMixin, CreateView):
    model = Neo4jMonitor
    form_class = Neo4jMonitorForm
    template_name = 'monitor/neo4j_form.html'
    success_url = reverse_lazy('neo4j_list')
    permission_required = 'monitor.add_neo4jmonitor'

    def get_initial(self):
        initial = super(Neo4jMonitorCreate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class Neo4jMonitorUpdate(PermissionRequiredMixin, UpdateView):
    model = Neo4jMonitor
    form_class = Neo4jMonitorForm
    context_object_name = 'neo4j_monitor'
    template_name = 'monitor/neo4j_form.html'
    permission_required = 'monitor.change_neo4jmonitor'

    def get_initial(self):
        initial = super(Neo4jMonitorUpdate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class Neo4jMonitorDetail(LoginRequiredMixin, DetailView):
    model = Neo4jMonitor
    context_object_name = 'neo4j_monitor'
    template_name = 'monitor/neo4j_detail.html'


class Neo4jMonitorInfo(Neo4jMonitorDetail):
    model = Neo4jMonitor
    context_object_name = 'object'
    template_name = 'monitor/monitor_view.html'

    def get_context_data(self, **kwargs):
        context = super(Neo4jMonitorInfo, self).get_context_data(**kwargs)
        context['title'] = 'Neo4j监控信息'
        node = NodeProxy(self.object.host, settings.NODE_PORT)
        try:
            context['monitor_info'] = node.netstat(self.object.port)
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            messages.error(self.request, "没连上主机: %s" % self.object.host)
        return context


class Neo4jMonitorDelete(PermissionRequiredMixin, DeleteView):
    model = Neo4jMonitor
    context_object_name = 'neo4j_monitor'
    template_name = 'monitor/neo4j_confirm_delete.html'
    success_url = reverse_lazy('neo4j_list')
    permission_required = 'monitor.delete_neo4jmonitor'


class Neo4jMonitorList(LoginRequiredMixin, ListView):
    model = Neo4jMonitor
    context_object_name = 'neo4j_monitor_list'
    template_name = 'monitor/neo4j_list.html'
    ordering = 'id'


# *******************************************************************************
# ActiveMQ
# *******************************************************************************


class ActiveMqMonitorCreate(PermissionRequiredMixin, CreateView):
    model = ActiveMqMonitor
    form_class = ActiveMqMonitorForm
    template_name = 'monitor/activemq_form.html'
    success_url = reverse_lazy('activemq_monitor_list_view')
    permission_required = 'monitor.add_activemqmonitor'

    def get_initial(self):
        initial = super(ActiveMqMonitorCreate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class ActiveMqMonitorUpdate(PermissionRequiredMixin, UpdateView):
    model = ActiveMqMonitor
    form_class = ActiveMqMonitorForm
    context_object_name = 'activemq_monitor'
    template_name = 'monitor/activemq_form.html'
    permission_required = 'monitor.change_activemqmonitor'

    def get_initial(self):
        initial = super(ActiveMqMonitorUpdate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class ActiveMqMonitorDetail(LoginRequiredMixin, DetailView):
    model = ActiveMqMonitor
    context_object_name = 'activemq_monitor'
    template_name = 'monitor/activemq_detail.html'


class ActiveMqMonitorInfo(ActiveMqMonitorDetail):
    context_object_name = 'activemq_monitor'
    template_name = 'monitor/activemq_monitor_view.html'

    def get_context_data(self, **kwargs):
        context = super(ActiveMqMonitorInfo, self).get_context_data(**kwargs)
        try:
            context['queues_info'] = self.object.get_queues_info()
        except Exception as e:
            messages.error(self.request, unicode(e))
            context['queues_info'] = []
        return context


class ActiveMqHistoryView(TemplateView):
    template_name = 'monitor/activemq_history_view.html'


class ActiveMqMonitorDelete(PermissionRequiredMixin, DeleteView):
    model = ActiveMqMonitor
    context_object_name = 'activemq_monitor'
    template_name = 'monitor/activemq_confirm_delete.html'
    success_url = reverse_lazy('activemq_monitor_list_view')
    permission_required = 'monitor.delete_activemqmonitor'


class ActiveMqMonitorList(LoginRequiredMixin, ListView):
    model = ActiveMqMonitor
    context_object_name = 'activemq_monitor_list'
    template_name = 'monitor/activemq_list.html'
    ordering = 'id'


# *******************************************************************************
# SpringCloud
# *******************************************************************************


class SpringCloudMonitorCreate(PermissionRequiredMixin, CreateView):
    model = SpringCloudMonitor
    form_class = SpringCloudMonitorForm
    template_name = 'monitor/springcloud_form.html'
    success_url = reverse_lazy('springcloud_monitor_list_view')
    permission_required = 'monitor.add_springcloudmonitor'

    def get_initial(self):
        initial = super(SpringCloudMonitorCreate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class SpringCloudMonitorUpdate(PermissionRequiredMixin, UpdateView):
    model = SpringCloudMonitor
    form_class = SpringCloudMonitorForm
    context_object_name = 'springcloud_monitor'
    template_name = 'monitor/springcloud_form.html'
    permission_required = 'monitor.change_springcloudmonitor'

    def get_initial(self):
        initial = super(SpringCloudMonitorUpdate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class SpringCloudMonitorDetail(LoginRequiredMixin, DetailView):
    model = SpringCloudMonitor
    context_object_name = 'springcloud_monitor'
    template_name = 'monitor/springcloud_detail.html'


class SpringCloudMonitorInfo(SpringCloudMonitorDetail):
    context_object_name = 'object'
    template_name = 'monitor/monitor_view.html'
    title = "SpringCloud监控信息"

    def get_context_data(self, **kwargs):
        context = super(SpringCloudMonitorInfo, self).get_context_data(**kwargs)
        context['title'] = self.title
        context['monitor_info'] = json.dumps(json.loads(self.object.health()), indent=4)
        return context


class SpringCloudMonitorDelete(PermissionRequiredMixin, DeleteView):
    model = SpringCloudMonitor
    context_object_name = 'springcloud_monitor'
    template_name = 'monitor/springcloud_confirm_delete.html'
    success_url = reverse_lazy('springcloud_monitor_list_view')
    permission_required = 'monitor.delete_springcloudmonitor'


class SpringCloudMonitorList(LoginRequiredMixin, ListView):
    model = SpringCloudMonitor
    context_object_name = 'springcloud_monitor_list'
    template_name = 'monitor/springcloud_list.html'
    ordering = '-id'


# *******************************************************************************
# Kafka
# *******************************************************************************


class KafkaMonitorCreate(PermissionRequiredMixin, CreateView):
    model = KafkaMonitor
    form_class = KafkaMonitorForm
    template_name = 'monitor/kafka_monitor_form.html'
    success_url = reverse_lazy('kafka_monitor_list_view')
    permission_required = 'monitor.add_kafkamonitor'

    def get_initial(self):
        initial = super(KafkaMonitorCreate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class KafkaMonitorUpdate(PermissionRequiredMixin, UpdateView):
    model = KafkaMonitor
    form_class = KafkaMonitorForm
    context_object_name = 'kafka_monitor'
    template_name = 'monitor/kafka_monitor_form.html'
    permission_required = 'monitor.change_kafkamonitor'

    def get_initial(self):
        initial = super(KafkaMonitorUpdate, self).get_initial()
        initial['created_by'] = self.request.user
        return initial


class KafkaMonitorDetail(LoginRequiredMixin, DetailView):
    model = KafkaMonitor
    context_object_name = 'kafka_monitor'
    template_name = 'monitor/kafka_monitor_detail.html'

    def get_context_data(self, **kwargs):
        context = super(KafkaMonitorDetail, self).get_context_data(**kwargs)
        try:
            self.object.create_zk()
            context['now_ids'] = json.dumps(self.object.get_ids())
            context['topics'] = self.object.get_topics()
        except Exception as e:
            messages.error(self.request, str(e))
            context['topics'] = []
        finally:
            self.object.destroy_zk()
        return context


class KafkaMonitorDelete(PermissionRequiredMixin, DeleteView):
    model = KafkaMonitor
    context_object_name = 'kafka_monitor'
    template_name = 'monitor/kafka_monitor_confirm_delete.html'
    success_url = reverse_lazy('kafka_monitor_list_view')
    permission_required = 'monitor.delete_kafkamonitor'


class KafkaMonitorList(LoginRequiredMixin, ListView):
    model = KafkaMonitor
    context_object_name = 'kafka_monitor_list'
    template_name = 'monitor/kafka_monitor_list.html'
    ordering = '-id'
