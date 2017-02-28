# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import (
    IdcList, IdcCreate, IdcUpdate, IdcDetail, IdcDelete,
    CabinetCreate, CabinetUpdate, CabinetDetail, CabinetDelete,
    ServerCheck, ServerCreate, ServerUpdate, ServerDetail, ServerDelete, ServerList,
    server_runtime_info,
    ProcessMonitorCreate, ProcessMonitorUpdate, ProcessMonitorDetail, ProcessMonitorDelete,
    NetworkDeviceCreate, NetworkDeviceUpdate, NetworkDeviceDetail, NetworkDeviceDelete,
    server_conf, server_process_monitors
)


urlpatterns = [
    url(r'^idc/create/$', IdcCreate.as_view(), name='idc_create'),
    url(r'^idc/(?P<pk>[0-9]+)/update/$', IdcUpdate.as_view(), name='idc_update'),
    url(r'^idc/(?P<pk>[0-9]+)/detail$', IdcDetail.as_view(), name='idc_detail'),
    url(r'^idc/(?P<pk>[0-9]+)/delete/$', IdcDelete.as_view(), name='idc_delete'),
    url(r'^idc/list/$', IdcList.as_view(), name='idc_list'),

    url(r'^idc/(\d+)/cabinet/create/$', CabinetCreate.as_view(), name='cabinet_create'),
    url(r'^cabinet/(?P<pk>[0-9]+)/update/$', CabinetUpdate.as_view(), name='cabinet_update'),
    url(r'^cabinet/(?P<pk>[0-9]+)/detail/$', CabinetDetail.as_view(), name='cabinet_detail'),
    url(r'^cabinet/(?P<pk>[0-9]+)/delete/$', CabinetDelete.as_view(), name='cabinet_delete'),

    url(r'^cabinet/(\d+)/server/check/$', ServerCheck.as_view(), name='server_check'),
    url(r'^cabinet/(\d+)/server/create/$', ServerCreate.as_view(), name='server_create'),
    url(r'^server/(?P<pk>[0-9]+)/update/$', ServerUpdate.as_view(), name='server_update'),
    url(r'^server/(?P<pk>[0-9]+)/detail/$', ServerDetail.as_view(), name='server_detail'),
    url(r'^server/(?P<pk>[0-9]+)/delete/$', ServerDelete.as_view(), name='server_delete'),
    url(r'^server/list/$', ServerList.as_view(), name='server_list'),

    url(r'^server/runtime-info/$', server_runtime_info, name='runtime_info'),

    url(r'^server/(\d+)/process-monitor/create/$', ProcessMonitorCreate.as_view(), name='process_monitor_create'),
    url(r'^process-monitor/(?P<pk>[0-9]+)/update/$', ProcessMonitorUpdate.as_view(), name='process_monitor_update'),
    url(r'^process-monitor/(?P<pk>[0-9]+)/detail/$', ProcessMonitorDetail.as_view(), name='process_monitor_detail'),
    url(r'^process-monitor/(?P<pk>[0-9]+)/delete/$', ProcessMonitorDelete.as_view(), name='process_monitor_delete'),

    url(r'^cabinet/(\d+)/network-device/create/$', NetworkDeviceCreate.as_view(), name='network_device_create'),
    url(r'^network-device/(?P<pk>[0-9]+)/update/$', NetworkDeviceUpdate.as_view(), name='network_device_update'),
    url(r'^network-device/(?P<pk>[0-9]+)/detail/$', NetworkDeviceDetail.as_view(), name='network_device_detail'),
    url(r'^network-device/(?P<pk>[0-9]+)/delete/$', NetworkDeviceDelete.as_view(), name='network_device_delete'),

    url(r'^server/conf/$', server_conf, name='server_conf'),
    url(r'^server/process-monitors/$', server_process_monitors, name='server_conf'),

]
