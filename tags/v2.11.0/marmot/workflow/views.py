# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.template import Context, loader
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.conf import settings

from workflow.models import Workflow
