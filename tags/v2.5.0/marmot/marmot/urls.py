# -*- coding: utf-8 -*-
from django.conf.urls import include, url
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings

from .views import index_view, send_alarm, redis_cache_log


urlpatterns = [
    url(r'^$', index_view),
    url(r'^alarm/$', send_alarm, name='alarm'),
    url(r'^redis-log/$', redis_cache_log, name='redis_cache_log'),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^assets/', include('assets.urls')),
    url(r'^services/', include('services.urls')),
    url(r'^script/', include('script.urls')),
    url(r'^task/', include('task.urls')),

    url(r'^admin/', include(admin.site.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
