# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import (
    NodeAppCreate, NodeAppUpdate, NodeAppDetail,
    NodeAppDelete, NodeAppList,

    NodeSrcPkgCreate, NodeSrcPkgDetail,
    NodeSrcPkgDelete, NodeSrcPkgList,

    push_node_src_pkg, push_node_pkg_log,
    start_node_app, kill_node_app
)


urlpatterns = [
    url(r'^app/create/$', NodeAppCreate.as_view(), name='node_app_create'),
    url(r'^app/(?P<pk>[0-9]+)/update/$', NodeAppUpdate.as_view(), name='node_app_update'),
    url(r'^app/(?P<pk>[0-9]+)/detail/$', NodeAppDetail.as_view(), name='node_app_detail'),
    url(r'^app/(?P<pk>[0-9]+)/delete/$', NodeAppDelete.as_view(), name='node_app_delete'),
    url(r'^app/list/$', NodeAppList.as_view(), name='node_app_list'),

    url(r'^app/(?P<pk>[0-9]+)/src-pkg/create/$', NodeSrcPkgCreate.as_view(), name='node_src_pkg_create'),
    url(r'^src-pkg/(?P<pk>[0-9]+)/detail/$', NodeSrcPkgDetail.as_view(), name='node_src_pkg_detail'),
    url(r'^src-pkg/(?P<pk>[0-9]+)/delete/$', NodeSrcPkgDelete.as_view(), name='node_src_pkg_delete'),
    url(r'^app/(?P<pk>[0-9]+)/src-pkg/list/$', NodeSrcPkgList.as_view(), name='node_src_pkg_list'),

    url(r'^(\d+)/startup/$', start_node_app, name='start_node_app'),
    url(r'^(\d+)/kill/$', kill_node_app, name='kill_node_app'),

    url(r'^push/src-pkg/$', push_node_src_pkg, name='push_node_src_pkg'),
    url(r'^push/src-pkg/log/$', push_node_pkg_log, name='push_node_pkg_log'),
]
