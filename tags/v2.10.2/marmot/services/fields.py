# -*- coding: utf-8 -*-
from django.db.models import DateTimeField


# TODO 优化DateTimeField字段的模板显示
class DDateTimeField(DateTimeField):
    def value_to_string(self, obj):
        val = self._get_val_from_obj(obj)
        return '' if val is None else val.strftime('%Y-%m-%d %H:%M:%S')
