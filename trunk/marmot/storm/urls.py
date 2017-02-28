# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import (
    StormClusterList,
    StormClusterCreate,
    StormClusterUpdate,
    StormClusterDetail,
    StormClusterDelete,
    StormNodeCreate,
    StormNodeUpdate,
    StormNodeDetail,
    StormNodeDelete,
    StormNodeList,
    StormAppCreate,
    StormAppUpdate,
    StormAppDetail,
    StormAppDelete,
    StormAppList,
    StormAppJarCreate,
    StormAppJarUpdate,
    StormAppJarDelete,
    StormAppJarList,
    active_jar_package,
    StormNodeJarDirCreate,
    StormNodeJarDirUpdate,
    StormNodeJarDirDelete,
    config_storm_app_node_jar_dir,
    get_storm_node_jar_dir,
    storm_node_switch,
    push_jar_to_storm,
    run_jar_to_storm,
)

urlpatterns = [
    url(r'^storm-cluster/list/$', StormClusterList.as_view(), name='storm_cluster_list'),
    url(r'^storm-cluster/create/$', StormClusterCreate.as_view(), name='storm_cluster_create'),
    url(r'^storm-cluster/(?P<pk>[0-9]+)/update/$', StormClusterUpdate.as_view(), name='storm_cluster_update'),
    url(r'^storm-cluster/(?P<pk>[0-9]+)/detail/$', StormClusterDetail.as_view(), name='storm_cluster_detail'),
    url(r'^storm-cluster/(?P<pk>[0-9]+)/delete/$', StormClusterDelete.as_view(), name='storm_cluster_delete'),

    url(r'^storm-cluster/(\d+)/storm-node/create/$', StormNodeCreate.as_view(), name='storm_node_create'),
    url(r'^storm-node/(?P<pk>[0-9]+)/update/$', StormNodeUpdate.as_view(), name='storm_node_update'),
    url(r'^storm-node/(?P<pk>[0-9]+)/detail/$', StormNodeDetail.as_view(), name='storm_node_detail'),
    url(r'^storm-node/(?P<pk>[0-9]+)/delete/$', StormNodeDelete.as_view(), name='storm_node_delete'),
    url(r'^storm-node/list/$', StormNodeList.as_view(), name='storm_node_list'),

    url(r'^storm-cluster/(\d+)/storm-app/create/$', StormAppCreate.as_view(), name='storm_app_create'),
    url(r'^storm-app/(?P<pk>[0-9]+)/update/$', StormAppUpdate.as_view(), name='storm_app_update'),
    url(r'^storm-app/(?P<pk>[0-9]+)/detail/$', StormAppDetail.as_view(), name='storm_app_detail'),
    url(r'^storm-app/(?P<pk>[0-9]+)/delete/$', StormAppDelete.as_view(), name='storm_app_delete'),
    url(r'^storm-app/list/$', StormAppList.as_view(), name='storm_app_list'),

    url(r'^storm-app/(\d+)/jar/create/$', StormAppJarCreate.as_view(), name='storm_app_jar_create'),
    url(r'^storm-app/jar/(?P<pk>[0-9]+)/update/$', StormAppJarUpdate.as_view(), name='storm_app_jar_update'),
    url(r'^storm-app/jar/(?P<pk>[0-9]+)/delete/$', StormAppJarDelete.as_view(), name='storm_app_jar_delete'),
    url(r'^storm-app/(\d+)/jar/list/$', StormAppJarList.as_view(), name='storm_app_jar_list'),
    url(r'^storm-app-jar/active/(\d+)/$', active_jar_package, name='active_jar'),


    url(r'^storm-node/(\d+)/storm-node-jar-dir/create/$', StormNodeJarDirCreate.as_view(), name='storm_node_jar_dir_create'),
    url(r'^storm-node-jar-dir/(?P<pk>[0-9]+)/update/$', StormNodeJarDirUpdate.as_view(), name='storm_node_jar_dir_update'),
    url(r'^storm-node-jar-dir/(?P<pk>[0-9]+)/delete/$', StormNodeJarDirDelete.as_view(), name='storm_node_jar_dir_delete'),

    url(r'^storm-app-node/config/jar-dir/$', config_storm_app_node_jar_dir, name='config_storm_app_node_jar_dir'),
    url(r'^storm-node/(\d+)/jar-dir/$', get_storm_node_jar_dir, name='get_storm_node_jar_dir'),

    url(r'^storm-node/(\d+)/switch/$', storm_node_switch, name='storm_node_switch'),
    url(r'^push/jar/(\d+)/(\d+)/$', push_jar_to_storm, name='push_jar_to_storm'),
    url(r'^run/jar/(\d+)/(\d+)/$', run_jar_to_storm, name='run_jar_to_storm'),
]
