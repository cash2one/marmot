# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import xmlrpclib

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.conf import settings


def connect_node(host, port=settings.NODE_PORT):
    return xmlrpclib.ServerProxy('http://%s:%s' % (host, port))


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
