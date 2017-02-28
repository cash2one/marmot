# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import (
    IceServiceCenterCreate, IceServiceCenterUpdate,
    IceServiceCenterList,  IceServiceCenterDelete, IceServiceCenterDetail,

    IceServiceCreate, IceServiceUpdate, IceServiceDetail, IceServiceDelete,

    IceServiceJarCreate, IceServiceJarUpdate, IceServiceJarList,
    active_jar_package, delete_jar_package,

    IceServiceConfigCreate, IceServiceConfigUpdate, IceServiceConfigList,
    active_config, delete_config,

    switch_ice_server_node_state, start_ice_service,
    sync_ice_service_xml, remove_ice_service, push_pkg_to_node,

    TomcatGroupCreate, TomcatGroupUpdate,
    TomcatGroupDetail, TomcatGroupDelete, TomcatGroupList,

    TomcatClusterCreate, TomcatClusterUpdate, TomcatClusterDetail, TomcatClusterDelete,

    TomcatServerCreate, TomcatServerUpdate,
    TomcatServerDetail, TomcatServerDelete, TomcatServerList,

    TomcatServerWarDirCreate, TomcatServerWarDirUpdate, TomcatServerWarDirDelete,

    TomcatAppCreate, TomcatAppUpdate, TomcatAppDetail, TomcatAppDelete,

    TomcatAppDBCreate, TomcatAppDBUpdate, TomcatAppDBDetail, TomcatAppDBDelete,

    TomcatAppWarCreate, TomcatAppWarUpdate,
    TomcatAppWarDelete, TomcatAppWarList, active_war_package,

    TomcatAppStaticCreate, TomcatAppStaticUpdate,
    TomcatAppStaticDelete, TomcatAppStaticList, active_static_package,

    TomcatAppSqlCreate, TomcatAppSqlUpdate, TomcatAppSqlDetail,
    TomcatAppSqlDelete, TomcatAppSqlList,

    tomcat_server_switch, push_war_to_tomcat,
    push_static_to_web_html, backup_database, execute_sql,
    config_tomcat_app_node_war_dir, get_tomcat_server_war_dir
)


urlpatterns = [
    url(r'^ice-service-center/list/$', IceServiceCenterList.as_view(), name='ice_service_center_list'),
    url(r'^ice-service-center/create/$', IceServiceCenterCreate.as_view(), name='ice_service_center_create'),
    url(r'^ice-service-center/update/(?P<pk>[0-9]+)/$', IceServiceCenterUpdate.as_view()),
    url(r'^ice-service-center/(?P<pk>[0-9]+)/$', IceServiceCenterDetail.as_view()),
    url(r'^ice-service-center/delete/(?P<pk>[0-9]+)/', IceServiceCenterDelete.as_view()),

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

    url(r'^ice-service-center/(\d+)/ice-service/create/$', IceServiceCreate.as_view(), name='ice_service_create'),
    url(r'^ice-service/(?P<pk>[0-9]+)/update/$', IceServiceUpdate.as_view(), name='ice_service_update'),
    url(r'^ice-service/(?P<pk>[0-9]+)/detail/$', IceServiceDetail.as_view(), name='ice_service_detail'),
    url(r'^ice-service/(?P<pk>[0-9]+)/delete/$', IceServiceDelete.as_view(), name='ice_service_delete'),

    url(r'^ice-service/(\d+)/push/$', push_pkg_to_node, name='push_ice_service_pkg'),
    url(r'^ice-service/(\d+)/start/$', start_ice_service, name='start_ice_service'),
    url(r'^ice-service/(\d+)/remove/$', remove_ice_service, name='remove_ice_service'),
    url(r'^ice-service/(\d+)/sync-xml/$', sync_ice_service_xml, name='sync_ice_service_xml'),

    url(r'^ice-service/(\d+)/node/([-, \w]+)/switch/(0|1)/$', switch_ice_server_node_state, name='ice_service_node_state'),

    url(r'^tomcat-group/create/$', TomcatGroupCreate.as_view(), name='tomcat_group_create'),
    url(r'^tomcat-group/(?P<pk>[0-9]+)/update/$', TomcatGroupUpdate.as_view(), name='tomcat_group_update'),
    url(r'^tomcat-group/(?P<pk>[0-9]+)/detail/$', TomcatGroupDetail.as_view(), name='tomcat_group_detail'),
    url(r'^tomcat-group/(?P<pk>[0-9]+)/delete/$', TomcatGroupDelete.as_view(), name='tomcat_group_delete'),
    url(r'^tomcat-group/list/$', TomcatGroupList.as_view(), name='tomcat_group_list'),

    url(r'^tomcat-group/(\d+)/tomcat-cluster/create/$', TomcatClusterCreate.as_view(), name='tomcat_cluster_create'),
    url(r'^tomcat-cluster/(?P<pk>[0-9]+)/update/$', TomcatClusterUpdate.as_view(), name='tomcat_cluster_update'),
    url(r'^tomcat-cluster/(?P<pk>[0-9]+)/detail/$', TomcatClusterDetail.as_view(), name='tomcat_cluster_detail'),
    url(r'^tomcat-cluster/(?P<pk>[0-9]+)/delete/&', TomcatClusterDelete.as_view(), name='tomcat_cluster_delete'),

    url(r'^tomcat-cluster/(\d+)/tomcat-server/create/$', TomcatServerCreate.as_view(), name='tomcat_server_create'),
    url(r'^tomcat-server/(?P<pk>[0-9]+)/update/$', TomcatServerUpdate.as_view(), name='tomcat_server_update'),
    url(r'^tomcat-server/(?P<pk>[0-9]+)/detail/$', TomcatServerDetail.as_view(), name='tomcat_server_detail'),
    url(r'^tomcat-server/(?P<pk>[0-9]+)/delete/$', TomcatServerDelete.as_view(), name='tomcat_server_delete'),
    url(r'^tomcat-server/list/$', TomcatServerList.as_view(), name='tomcat_server_list'),

    url(r'^tomcat-server/(\d+)/switch/$', tomcat_server_switch, name='tomcat_server_switch'),

    url(r'^tomcat-server/(\d+)/tomcat-server-war-dir/create/$', TomcatServerWarDirCreate.as_view(), name='tomcat_server_war_dir_create'),
    url(r'^tomcat-server-war-dir/(?P<pk>[0-9]+)/update/$', TomcatServerWarDirUpdate.as_view(), name='tomcat_server_war_dir_update'),
    url(r'^tomcat-server-war-dir/(?P<pk>[0-9]+)/delete/$', TomcatServerWarDirDelete.as_view(), name='tomcat_server_war_dir_delete'),

    url(r'^tomcat-cluster/(\d+)/tomcat-app/create/$', TomcatAppCreate.as_view(), name='tomcat_app_create'),
    url(r'^tomcat-app/(?P<pk>[0-9]+)/update/$', TomcatAppUpdate.as_view(), name='tomcat_app_update'),
    url(r'^tomcat-app/(?P<pk>[0-9]+)/detail/$', TomcatAppDetail.as_view(), name='tomcat_app_detail'),
    url(r'^tomcat-app/(?P<pk>[0-9]+)/delete/$', TomcatAppDelete.as_view(), name='tomcat_app_delete'),

    url(r'^tomcat-app-node/config/war-dir/$', config_tomcat_app_node_war_dir, name='config_tomcat_app_node_war_dir'),
    url(r'^tomcat-server/(\d+)/war-dir/$', get_tomcat_server_war_dir, name='get_tomcat_server_war_dir'),

    url(r'^tomcat-app/(\d+)/db/create/$', TomcatAppDBCreate.as_view(), name='tomcat_app_db_create'),
    url(r'^tomcat-app/db/(?P<pk>[0-9]+)/update/$', TomcatAppDBUpdate.as_view(), name='tomcat_app_db_update'),
    url(r'^tomcat-app/db/(?P<pk>[0-9]+)/detail/$', TomcatAppDBDetail.as_view(), name='tomcat_app_db_detail'),
    url(r'^tomcat-app/db/(?P<pk>[0-9]+)/delete/$', TomcatAppDBDelete.as_view(), name='tomcat_app_db_delete'),

    url(r'^tomcat-app/(\d+)/war/create/$', TomcatAppWarCreate.as_view(), name='tomcat_app_war_create'),
    url(r'^tomcat-app/war/(?P<pk>[0-9]+)/update/$', TomcatAppWarUpdate.as_view(), name='tomcat_app_war_update'),
    url(r'^tomcat-app/war/(?P<pk>[0-9]+)/delete/$', TomcatAppWarDelete.as_view(), name='tomcat_app_war_delete'),
    url(r'^tomcat-app/(\d+)/war/list/$', TomcatAppWarList.as_view(), name='tomcat_app_war_list'),
    url(r'^tomcat-app-war/active/(\d+)/$', active_war_package, name='active_war'),

    url(r'^tomcat-app/(\d+)/static/create/$', TomcatAppStaticCreate.as_view(), name='tomcat_app_static_create'),
    url(r'^tomcat-app/static/(?P<pk>[0-9]+)/update/$', TomcatAppStaticUpdate.as_view(), name='tomcat_app_static_update'),
    url(r'^tomcat-app/static/(?P<pk>[0-9]+)/delete/$', TomcatAppStaticDelete.as_view(), name='tomcat_app_static_delete'),
    url(r'^tomcat-app/(\d+)/static/list/$', TomcatAppStaticList.as_view(), name='tomcat_app_static_list'),
    url(r'^tomcat-app-static/(\d+)/active/$', active_static_package, name='active_static'),

    url(r'^tomcat-app/(\d+)/sql/create/$', TomcatAppSqlCreate.as_view(), name='tomcat_app_sql_create'),
    url(r'^tomcat-app/sql/(?P<pk>[0-9]+)/update/$', TomcatAppSqlUpdate.as_view(), name='tomcat_app_sql_update'),
    url(r'^tomcat-app/sql/(?P<pk>[0-9]+)/delete/$', TomcatAppSqlDelete.as_view(), name='tomcat_app_sql_delete'),
    url(r'^tomcat-app/sql/(?P<pk>[0-9]+)/detail/$', TomcatAppSqlDetail.as_view(), name='tomcat_app_sql_detail'),
    url(r'^tomcat-app/(\d+)/sql/list/$', TomcatAppSqlList.as_view(), name='tomcat_app_sql_list'),

    url(r'^push/war/(\d+)/(\d+)/$', push_war_to_tomcat, name='push_war_to_tomcat'),
    url(r'^push/static/(\d+)/(\d+)/$', push_static_to_web_html, name='push_static_to_web_html'),
    url(r'^backup/db/(\d+)/$', backup_database, name='backup_database'),
    url(r'^execute/sql/(\d+)/$', execute_sql, name='execute_sql'),
]
