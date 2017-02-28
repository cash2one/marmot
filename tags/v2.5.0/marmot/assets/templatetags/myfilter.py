# -*- coding: utf-8 -*-

from django import template


register = template.Library()


@register.filter
def get_dict_val(d, k):
    try:
        return d[k]
    except KeyError:
        return ''
