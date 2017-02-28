# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group

from bralarm import send_alarm_to_personal


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
    group = Group.objects.get_by_natural_key('alarm')
    users = User.objects.filter(groups=group).all()
    host = request.GET.get('host')
    level = request.GET.get('level')
    type_ = request.GET.get('type')
    msg = request.GET.get('msg')
    mails = [user.email for user in users]
    cells = [user.profile.cell for user in users]
    ret = send_alarm_to_personal(mails=','.join(mails), msgs=','.join(cells), alarmType=1,
                                 mailContent=msg, mailTitle='【Marmot】服务器警报', msgContent=msg)
    return JsonResponse({'msg':  0 if ret else 'error'})
