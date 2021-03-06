#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import hashlib
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marmot.settings")
django.setup()

from services.models import IceServiceJar, IceServiceConfig, TomcatAppWar


for jar in IceServiceJar.objects.all():
    if jar.md5:
        continue
    jar.save()


for conf in IceServiceConfig.objects.all():
    if conf.md5:
        continue
    conf.save()


for war in TomcatAppWar.objects.all():
    if war.md5:
        continue
    war.save()
