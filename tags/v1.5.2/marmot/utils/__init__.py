# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import time
import xmlrpclib

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.conf import settings


def connect_node(host, port=settings.NODE_PORT):
    return xmlrpclib.ServerProxy('http://%s:%s' % (host, port))


def backup_database(host, port, user, pwd, db):
    bak = 'bak-{0}-{1}.sql'.format(db, time.strftime('%Y-%m-%d-%H-%M-%S'))
    bak = os.path.join('/tmp/', bak)
    cmd = 'mysqldump -h{host} --port={port} -u{user} --password={pwd} {db} > {bak};'.format(
        host=host, port=port, user=user, pwd=pwd, db=db, bak=bak
    )
    ret = os.system(cmd)
    if ret:
        raise RuntimeError('mysqldump error')
    else:
        return os.path.abspath(bak)


def execute_sql(host, port, user, pwd, db, sql):
    cmd = 'mysql -h{host} --port={port} -u{user} --password={pwd} {db} < {sql};'.format(
        host=host, port=port, user=user, pwd=pwd, db=db, sql=sql
    )
    return os.system(cmd)


def serialize_form_errors(form):
    errors = []
    for field in form:
        if field.errors:
            errors.append(field.label + ':' + ','.join([err for err in field.errors]))
    return '\n'.join(errors)


def paginate(data, current_page=1, page_num=20):
    paginator = Paginator(data, page_num)
    try:
        show_lines = paginator.page(current_page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        show_lines = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        show_lines = paginator.page(paginator.num_pages)
    return show_lines
