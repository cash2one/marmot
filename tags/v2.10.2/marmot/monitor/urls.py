# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import (
    RedisClusterMonitorCreate, RedisClusterMonitorUpdate, RedisClusterMonitorDetail,
    RedisClusterInfo, RedisClusterMonitorDelete, RedisClusterMonitorList,
    RedisNodeCreate, RedisNodeUpdate, RedisNodeDetail, RedisNodeInfo, RedisNodeDelete,
    HBaseClusterMonitorCreate, HBaseClusterMonitorUpdate, HBaseClusterMonitorDetail,
    HBaseClusterMonitorInfo, HBaseClusterMonitorDelete, HBaseClusterMonitorList,
    ESMonitorCreate, ESMonitorUpdate, ESMonitorDetail, ESMonitorInfo,
    ESMonitorDelete, ESMonitorList,
    Neo4jMonitorCreate, Neo4jMonitorUpdate, Neo4jMonitorDetail, Neo4jMonitorInfo,
    Neo4jMonitorDelete, Neo4jMonitorList
)


urlpatterns = [
    url(r'^rc/create/$', RedisClusterMonitorCreate.as_view(), name='redis_cluster_create'),
    url(r'^rc/(?P<pk>[0-9]+)/update/$', RedisClusterMonitorUpdate.as_view(), name='redis_cluster_update'),
    url(r'^rc/(?P<pk>[0-9]+)/detail$', RedisClusterMonitorDetail.as_view(), name='redis_cluster_detail'),
    url(r'^rc/(?P<pk>[0-9]+)/info', RedisClusterInfo.as_view(), name='redis_cluster_runtime_info'),
    url(r'^rc/(?P<pk>[0-9]+)/delete/$', RedisClusterMonitorDelete.as_view(), name='redis_cluster_delete'),
    url(r'^rc/list/$', RedisClusterMonitorList.as_view(), name='redis_cluster_list'),

    url(r'^rc/(\d+)/rn/create/$', RedisNodeCreate.as_view(), name='redis_node_create'),
    url(r'^rn/(?P<pk>[0-9]+)/update/$', RedisNodeUpdate.as_view(), name='redis_node_update'),
    url(r'^rn/(?P<pk>[0-9]+)/detail/$', RedisNodeDetail.as_view(), name='redis_node_detail'),
    url(r'^rn/(?P<pk>[0-9]+)/info/$', RedisNodeInfo.as_view(), name='redis_node_runtime_info'),
    url(r'^rn/(?P<pk>[0-9]+)/delete/$', RedisNodeDelete.as_view(), name='redis_node_delete'),

    url(r'^hbc/create/$', HBaseClusterMonitorCreate.as_view(), name='hbase_cluster_create'),
    url(r'^hbc/(?P<pk>[0-9]+)/update/$', HBaseClusterMonitorUpdate.as_view(), name='hbase_cluster_update'),
    url(r'^hbc/(?P<pk>[0-9]+)/detail/$', HBaseClusterMonitorDetail.as_view(), name='hbase_cluster_detail'),
    url(r'^hbc/(?P<pk>[0-9]+)/info/$', HBaseClusterMonitorInfo.as_view(), name='hbase_cluster_runtime_info'),
    url(r'^hbc/(?P<pk>[0-9]+)/delete/$', HBaseClusterMonitorDelete.as_view(), name='hbase_cluster_delete'),
    url(r'^hbc/list/$', HBaseClusterMonitorList.as_view(), name='hbase_cluster_list'),

    url(r'^es/create/$', ESMonitorCreate.as_view(), name='es_create'),
    url(r'^es/(?P<pk>[0-9]+)/update/$', ESMonitorUpdate.as_view(), name='es_update'),
    url(r'^es/(?P<pk>[0-9]+)/detail/$', ESMonitorDetail.as_view(), name='es_detail'),
    url(r'^es/(?P<pk>[0-9]+)/info/$', ESMonitorInfo.as_view(), name='es_runtime_info'),
    url(r'^es/(?P<pk>[0-9]+)/delete/$', ESMonitorDelete.as_view(), name='es_delete'),
    url(r'^es/list/$', ESMonitorList.as_view(), name='es_list'),

    url(r'^neo4j/create/$', Neo4jMonitorCreate.as_view(), name='neo4j_create'),
    url(r'^neo4j/(?P<pk>[0-9]+)/update/$', Neo4jMonitorUpdate.as_view(), name='neo4j_update'),
    url(r'^neo4j/(?P<pk>[0-9]+)/detail/$', Neo4jMonitorDetail.as_view(), name='neo4j_detail'),
    url(r'^neo4j/(?P<pk>[0-9]+)/info/$', Neo4jMonitorInfo.as_view(), name='neo4j_runtime_info'),
    url(r'^neo4j/(?P<pk>[0-9]+)/delete/$', Neo4jMonitorDelete.as_view(), name='neo4j_delete'),
    url(r'^neo4j/list/$', Neo4jMonitorList.as_view(), name='neo4j_list'),
]
