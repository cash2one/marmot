#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marmot.settings")
django.setup()

from workflow.models import WorkflowActivity


for w in WorkflowActivity.objects.all():
    h = w.history.first()
    if h:
        w.current_state = h.state
        w.save()
