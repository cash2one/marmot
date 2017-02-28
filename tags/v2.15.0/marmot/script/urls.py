# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import (
    ScriptCreate, ScriptUpdate, ScriptDetail, ScriptDelete, ScriptList,
    run_script, script_implement_log_view, script_implement_log
)


urlpatterns = [
    url(r'^create/$', ScriptCreate.as_view(), name='script_create'),
    url(r'^update/(?P<pk>[0-9]+)/$', ScriptUpdate.as_view(), name='script_update'),
    url(r'^(?P<pk>[0-9]+)/$', ScriptDetail.as_view(), name='script_detail'),
    url(r'^delete/(?P<pk>[0-9]+)/$', ScriptDelete.as_view(), name='script_delete'),
    url(r'^list/$', ScriptList.as_view(), name='script_list'),

    url(r'^(\d+)/run/$', run_script, name='run_script'),
    url(r'^(\d+)/implement/log/view$', script_implement_log_view, name='script_implement_log_view'),
    url(r'^(\w+)/implement/log/$', script_implement_log, name='script_implement_log'),
]
