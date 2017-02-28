# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import task_implement_log, node_task_log_view


urlpatterns = [
    url(r'^implement/log/([-, \w]+)/$', task_implement_log, name='task_implement_log'),
    url(r'^implement/log/view/([-,\w]+)/$', node_task_log_view, name='node_task_log_view'),
]
