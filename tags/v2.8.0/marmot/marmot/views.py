# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import json
import redis

from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.views.decorators.csrf import csrf_exempt

from pyalarm.bralarm import send_alarm_to_personal


RDS = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)

errlog = logging.getLogger('marmot')


@login_required
def index_view(request):
    if not request.user.is_authenticated():
        return redirect('/accounts/login')
    role = request.user.profile.role.alias
    if role == 'CPIS':
        return redirect('/assets/idc/list/')
    elif role == 'developer':
        return redirect('/assets/server/list')
    else:
        return redirect('/accounts/login')


def send_alarm(request):
    users = Group.objects.get_by_natural_key('alarm').user_set.all()
    # host = request.GET.get('host')
    # level = request.GET.get('level')
    # type_ = request.GET.get('type')
    msg = request.GET.get('msg')
    mails = [user.email for user in users]
    cells = [user.profile.cell for user in users]
    ret = send_alarm_to_personal(mails=','.join(mails), msgs=','.join(cells), alarmType=1,
                                 mailContent=msg, mailTitle='Marmot -- 服务器警报', msgContent=msg)
    return JsonResponse({'msg':  0 if ret else 'error'})


@csrf_exempt
def redis_cache_log(request):
    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({'msg':  1})
    act = data.get('act')
    identifier = data.get('id')
    if act == 'init':
        RDS.delete(identifier)
        RDS.rpush(identifier, ' * '*16 + ' Marmot ' + ' * '*16)
        RDS.rpush(identifier, '任务标识: %s' % identifier)
        RDS.expire(identifier, 60 * 5)
        return JsonResponse({'msg':  0})
    elif act == 'log':
        RDS.rpush(identifier, data.get('msg'))
        return JsonResponse({'msg':  0})
    else:
        return JsonResponse({'msg':  1})
