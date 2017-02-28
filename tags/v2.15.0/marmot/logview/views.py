# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

import redis


RDS = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)


@login_required
def node_task_log_view(request, identifier):
    return render(request, 'logview/node_task_log_view.html', {'identifier': identifier})


@login_required
def task_implement_log(request, identifier):
    return JsonResponse({'msg': [RDS.lpop(identifier) for _ in range(RDS.llen(identifier))]})


# TODO 需要将上面那个替换成下面的, 为不影响历史的代码, 暂时并存
@login_required
def task_implement_log2(request):
    identifier = request.GET.get('ident')
    return JsonResponse({'msg': [RDS.lpop(identifier) for _ in range(RDS.llen(identifier))]})
