# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import (
    IdcList, IdcCreate, IdcUpdate, IdcDetail, IdcDelete,
    CabinetCreate, CabinetUpdate, CabinetDetail, CabinetDelete,
    ServerAdd, ServerUpdate, ServerDetail, ServerDelete, ServerList, server_online_list, server_runtime_info,
    NetworkDeviceCreate, NetworkDeviceUpdate, NetworkDeviceDetail, NetworkDeviceDelete,
    server_conf
)


urlpatterns = [
    url(r'^idc/list/$', IdcList.as_view(), name='idc_list'),
    url(r'^idc/create/$', IdcCreate.as_view(), name='idc_create'),
    url(r'^idc/(?P<pk>[0-9]+)/$', IdcDetail.as_view()),
    url(r'^idc/update/(?P<pk>[0-9]+)/$', IdcUpdate.as_view()),
    url(r'^idc/delete/(?P<pk>[0-9]+)/$', IdcDelete.as_view()),

    url(r'^idc/([0-9]+)/cabinet/create/$', CabinetCreate.as_view()),
    url(r'^cabinet/(?P<pk>[0-9]+)/$', CabinetDetail.as_view()),
    url(r'^cabinet/update/(?P<pk>[0-9]+)/$', CabinetUpdate.as_view()),
    url(r'^cabinet/delete/(?P<pk>[0-9]+)/$', CabinetDelete.as_view()),

    url(r'^cabinet/([0-9]+)/server/add/$', ServerAdd.as_view(), name='server_add'),
    url(r'^server/(?P<pk>[0-9]+)/$', ServerDetail.as_view(), name='server_detail'),
    url(r'^server/update/(?P<pk>[0-9]+)/$', ServerUpdate.as_view()),
    url(r'^server/delete/(?P<pk>[0-9]+)/$', ServerDelete.as_view()),
    url(r'^server/list/$', ServerList.as_view(), name='server_list'),

    url(r'^server-online/list/$', server_online_list, name='server_online_list'),
    url(r'^server/runtime-info/$', server_runtime_info, name='runtime_info'),

    url(r'^cabinet/([0-9]+)/network-device/create/$', NetworkDeviceCreate.as_view()),
    url(r'^network-device/(?P<pk>[0-9]+)/$', NetworkDeviceDetail.as_view()),
    url(r'^network-device/update/(?P<pk>[0-9]+)/$', NetworkDeviceUpdate.as_view()),
    url(r'^network-device/delete/(?P<pk>[0-9]+)/$', NetworkDeviceDelete.as_view()),

    url(r'^server/conf/$', server_conf, name='server_conf'),
]
