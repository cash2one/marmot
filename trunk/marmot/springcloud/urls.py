# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import (
    SpringCloudClusterCreate, SpringCloudClusterUpdate,
    SpringCloudClusterDetail, SpringCloudClusterDelete,
    SpringCloudClusterList,

    SpringCloudNodeCreate, SpringCloudNodeUpdate,
    SpringCloudNodeDetail, SpringCloudNodeDelete,

    SpringCloudAppCreate, SpringCloudAppUpdate,
    SpringCloudAppDetail, SpringCloudAppDelete,
    start_springcloud_app, kill_springcloud_app,
    sync_springcloud_files,

    springcloud_file_upload, SpringCloudFileList,
    springcloud_file_delete,

    springcloud_backup_create, springcloud_backup_delete,
    springcloud_rollback, SpringCloudBackupList, springcloud_backup_options
)


urlpatterns = [
    url(r'^cluster/create/$', SpringCloudClusterCreate.as_view(), name='springcloud_cluster_create'),
    url(r'^cluster/(?P<pk>[0-9]+)/update/$', SpringCloudClusterUpdate.as_view(), name='springcloud_cluster_update'),
    url(r'^cluster/(?P<pk>[0-9]+)/detail/$', SpringCloudClusterDetail.as_view(), name='springcloud_cluster_detail'),
    url(r'^cluster/(?P<pk>[0-9]+)/delete/$', SpringCloudClusterDelete.as_view(), name='springcloud_cluster_delete'),
    url(r'^cluster/list/$', SpringCloudClusterList.as_view(), name='springcloud_cluster_list'),

    url(r'^cluster/(?P<pk>[0-9]+)/node/create/$', SpringCloudNodeCreate.as_view(), name='springcloud_node_create'),
    url(r'^node/(?P<pk>[0-9]+)/update/$', SpringCloudNodeUpdate.as_view(), name='springcloud_node_update'),
    url(r'^node/(?P<pk>[0-9]+)/detail/$', SpringCloudNodeDetail.as_view(), name='springcloud_node_detail'),
    url(r'^node/(?P<pk>[0-9]+)/delete/$', SpringCloudNodeDelete.as_view(), name='springcloud_node_delete'),

    url(r'^cluster/(?P<pk>[0-9]+)/app/create/$', SpringCloudAppCreate.as_view(), name='springcloud_app_create'),
    url(r'^app/(?P<pk>[0-9]+)/update/$', SpringCloudAppUpdate.as_view(), name='springcloud_app_update'),
    url(r'^app/(?P<pk>[0-9]+)/detail/$', SpringCloudAppDetail.as_view(), name='springcloud_app_detail'),
    url(r'^app/(?P<pk>[0-9]+)/delete/$', SpringCloudAppDelete.as_view(), name='springcloud_app_delete'),

    url(r'^app/(?P<app>[0-9]+)/files/(?P<type>[0-9]+)/upload/$', springcloud_file_upload, name='springcloud_file_upload'),
    url(r'^app/(?P<app>[0-9]+)/files/(?P<type>[0-9]+)/$', SpringCloudFileList.as_view(), name='springcloud_file_list'),
    url(r'^file/delete/$', springcloud_file_delete, name='springcloud_file_delete'),

    url(r'^app/(\d+)/startup/$', start_springcloud_app, name='start_springcloud_app'),
    url(r'^app/(\d+)/kill/$', kill_springcloud_app, name='kill_springcloud_app'),
    url(r'^app/(\d+)/sync/$', sync_springcloud_files, name='sync_springcloud_files'),

    url(r'^backup/create/$', springcloud_backup_create, name='springcloud_backup_create'),
    url(r'^backup/delete/$', springcloud_backup_delete, name='springcloud_backup_delete'),
    url(r'^backup/rollback/$', springcloud_rollback, name='springcloud_rollback'),
    url(r'^backup/options/$', springcloud_backup_options, name='springcloud_backup_options'),
    url(r'^backup/list/(?P<app>[0-9]+)/$', SpringCloudBackupList.as_view(), name='springcloud_backup_list_view'),
]
