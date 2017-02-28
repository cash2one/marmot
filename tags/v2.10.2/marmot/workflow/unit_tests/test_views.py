# -*- coding: UTF-8 -*-
"""
View tests for Workflows
"""
import datetime

from django.conf import settings
from django.test.client import Client
from django.test import TestCase

from workflow.models import Workflow
from workflow.views import *
