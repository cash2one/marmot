# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import (
    TaskDetail, TaskList, TaskDelete, TaskIceAppCreate,
    TaskFirewallCreate, TaskTomcatAppCreate, TaskDNSCreate,
    TaskSpringCloudAppCreate,
    progress_transition, add_comment, assign_te,
)


urlpatterns = [
    url(r'^firewall/create/$', TaskFirewallCreate.as_view(), name='task_firewall_create'),
    url(r'^ice-service/create/$', TaskIceAppCreate.as_view(), name='task_ice_create'),
    url(r'^dns/create/$', TaskDNSCreate.as_view(), name='task_dns_create'),
    url(r'^tomcat-app/create/$', TaskTomcatAppCreate.as_view(), name='task_tomcat_app_create'),
    url(r'^springcloud/create/$', TaskSpringCloudAppCreate.as_view(), name='task_springcloud_create'),
    url(r'^list/$', TaskList.as_view(), name='task_list'),
    url(r'^(?P<pk>[0-9]+)/detail/$', TaskDetail.as_view(), name='task_detail'),
    url(r'^(?P<pk>[0-9]+)/delete/$', TaskDelete.as_view(), name='task_delete'),
    url(r'^(\d+)/progress/transition/$', progress_transition, name='progress_transition'),
    url(r'^(\d+)/add/comment/$', add_comment, name='add_comment'),
    url(r'^(\d+)/assign/te/$', assign_te, name='assign_te'),
]
