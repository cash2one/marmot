# -*- coding: utf-8 -*-
from django.db import models


class IntegerRangeField(models.IntegerField):
    description = "Integer Range Field"

    def __init__(self, verbose_name=None, name=None, min_value=None, max_value=None, **kwargs):
        self.min_value, self.max_value = min_value, max_value
        models.IntegerField.__init__(self, verbose_name, name, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'min_value': self.min_value, 'max_value': self.max_value}
        defaults.update(kwargs)
        return super(IntegerRangeField, self).formfield(**defaults)


class PortField(models.IntegerField):
    description = "Port[0, 65535]"

    def formfield(self, **kwargs):
        defaults = {'min_value': 0, 'max_value': 65535}
        defaults.update(kwargs)
        return super(PortField, self).formfield(**defaults)
