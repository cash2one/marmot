# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import (
    IceServiceCenterCreate, IceServiceCenterUpdate, IceServiceCenterList, IceServiceCenterDelete,
    IceServiceCenterDetail,
    IceServiceNodeCreate, IceServiceNodeUpdate, IceServiceNodeDetail, IceServiceNodeDelete,
    IceServiceCreate, IceServiceUpdate, IceServiceDetail, IceServiceDelete,
    IceServiceJarCreate, IceServiceJarUpdate, active_jar_package, delete_jar_package, IceServiceJarList,
    IceServiceConfigCreate, IceServiceConfigUpdate, active_config, delete_config, IceServiceConfigList,
    switch_ice_server_node_state, start_ice_service, sync_ice_service_xml,
    remove_ice_service, push_pkg_to_node,
    ScriptCreate, ScriptUpdate, ScriptDetail, ScriptDelete, ScriptList,
    run_script, script_implement_log_view, script_implement_log
)


urlpatterns = [
    url(r'^ice-service-center/list/$', IceServiceCenterList.as_view(), name='ice_service_center_list'),
    url(r'^ice-service-center/create/$', IceServiceCenterCreate.as_view(), name='ice_service_center_create'),
    url(r'^ice-service-center/update/(?P<pk>[0-9]+)/$', IceServiceCenterUpdate.as_view()),
    url(r'^ice-service-center/(?P<pk>[0-9]+)/$', IceServiceCenterDetail.as_view()),
    url(r'^ice-service-center/delete/(?P<pk>[0-9]+)/', IceServiceCenterDelete.as_view()),

    url(r'^ice-service-center/([0-9]+)/ice-service-node/create/$', IceServiceNodeCreate.as_view(), name='ice_service_node_create'),
    url(r'^ice-service-node/update/(?P<pk>[0-9]+)/$', IceServiceNodeUpdate.as_view()),
    url(r'^ice-service-node/(?P<pk>[0-9]+)/$', IceServiceNodeDetail.as_view()),
    url(r'^ice-service-node/delete/(?P<pk>[0-9]+)/$', IceServiceNodeDelete.as_view()),

    url(r'^ice-service/(\d+)/create/jar/$', IceServiceJarCreate.as_view(), name='ice_service_jar_create'),
    url(r'^ice-service-jar/update/(?P<pk>[0-9]+)/$', IceServiceJarUpdate.as_view(), name='ice_service_jar_update'),
    url(r'^ice-service-jar/delete/(\d+)/$', delete_jar_package, name='delete_jar'),
    url(r'^ice-service-jar/active/(\d+)/$', active_jar_package, name='active_jar'),
    url(r'^ice-service/(?P<ice_service_id>[0-9]+)/jar/list/$', IceServiceJarList.as_view(), name='ice_service_jar_list'),

    url(r'^ice-service/(\d+)/create/config/$', IceServiceConfigCreate.as_view(), name='ice_service_config_create'),
    url(r'^ice-service-config/update/(?P<pk>[0-9]+)/$', IceServiceConfigUpdate.as_view(), name='ice_service_config_update'),
    url(r'^ice-service-config/delete/(\d+)/$', delete_config, name='delete_config'),
    url(r'^ice-service-config/active/(\d+)/$', active_config, name='active_config'),
    url(r'^ice-service/(?P<ice_service_id>[0-9]+)/config/list/$', IceServiceConfigList.as_view(), name='ice_service_config_list'),

    url(r'^ice-service-center/([0-9]+)/ice-service/create/$', IceServiceCreate.as_view(), name='ice_service_create'),
    url(r'^ice-service/update/(?P<pk>[0-9]+)/$', IceServiceUpdate.as_view()),
    url(r'^ice-service/(?P<pk>[0-9]+)/$', IceServiceDetail.as_view()),
    url(r'^ice-service/delete/(?P<pk>[0-9]+)/$', IceServiceDelete.as_view()),

    url(r'^ice-service/(\d+)/push/$', push_pkg_to_node, name='push_ice_service_pkg'),
    url(r'^ice-service/(\d+)/start/$', start_ice_service, name='start_ice_service'),
    url(r'^ice-service/(\d+)/remove/$', remove_ice_service, name='remove_ice_service'),
    url(r'^ice-service/(\d+)/sync-xml/$', sync_ice_service_xml, name='sync_ice_service_xml'),

    url(r'^ice-service/(\d+)/node/([-, \w]+)/switch/(0|1)/$', switch_ice_server_node_state, name='ice_service_node_state'),

    url(r'^script/create/$', ScriptCreate.as_view(), name='script_create'),
    url(r'^script/update/(?P<pk>[0-9]+)/$', ScriptUpdate.as_view(), name='script_update'),
    url(r'^script/(?P<pk>[0-9]+)/$', ScriptDetail.as_view()),
    url(r'^script/delete/(?P<pk>[0-9]+)/$', ScriptDelete.as_view()),
    url(r'^script/list/$', ScriptList.as_view(), name='script_list'),

    url(r'^script/(\d+)/run/$', run_script, name='run_script'),
    url(r'^script/(\d+)/implement/log/view$', script_implement_log_view, name='script_implement_log_view'),
    url(r'^script/(\w+)/implement/log/$', script_implement_log, name='script_implement_log'),
]
