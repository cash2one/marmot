# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
from celery import Celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marmot.settings')

app = Celery('marmot')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


# $ celery -A marmot worker -l info
# $ celery -A tasks worker --loglevel=info
# $ ps auxww | grep 'celery worker' | awk '{print $2}' | xargs kill -9
# $ celery -A marmot beat -l info
