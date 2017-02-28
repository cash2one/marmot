# -*- coding: utf-8 -*-
import uuid

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def gen_uuid4():
    """
    生成uuid 用来做task-id
    """
    return mark_safe(uuid.uuid4().get_hex())
