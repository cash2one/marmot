# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import (
    TaskDetail, TaskList, TaskDelete, assign_operator, set_task_progress, task_implement_log,
    node_task_log_view, TaskIceServiceCreate, TaskFirewallCreate, TaskTomcatAppCreate
)


urlpatterns = [
    url(r'^firewall/create/$', TaskFirewallCreate.as_view(), name='task_firewall_create'),
    url(r'^ice-service/create/$', TaskIceServiceCreate.as_view(), name='task_ice_create'),
    url(r'^tomcat-app/create/$', TaskTomcatAppCreate.as_view(), name='task_tomcat_app_create'),
    url(r'^list/$', TaskList.as_view(), name='task_list'),
    url(r'^(?P<pk>[0-9]+)/$', TaskDetail.as_view()),
    url(r'^delete/(?P<pk>[0-9]+)/$', TaskDelete.as_view()),
    url(r'^assign/([0-9]+)/$', assign_operator, name='assign_operator'),
    url(r'^set/([0-9]+)/progress/([0-9]+)/$', set_task_progress, name='set_task_progress'),

    url(r'^implement/log/([-, \w]+)/$', task_implement_log, name='task_implement_log'),
    url(r'^implement/log/view/([-,\w]+)/$', node_task_log_view, name='node_task_log_view'),
]
