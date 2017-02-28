# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from utils import send_html_mail


def html_mail_format(title, type_, content):
    message = '<h3>{title}</h3>' \
              '<p>警报类型： {type}</p>' \
              '<p>{content}</p>'.format(title=title, type=type_, content=content)
    return message
