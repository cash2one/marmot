# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.core.mail import EmailMessage

from celery import current_app as app
from celery.utils.log import get_task_logger


logger = get_task_logger(__name__)


@app.task(name='celerymail.send_html_mail')
def send_html_mail(subject, html_content, recipient_list):
    logger.info('celerymail.send_html_mail - %s' % subject)
    msg = EmailMessage(subject, html_content, settings.EMAIL_HOST_USER, recipient_list)
    msg.content_subtype = 'html'  # main content is now text/html
    try:
        msg.send(fail_silently=False)
    except Exception:
        logger.exception('ERROR: celerymail.send_html_mail')
