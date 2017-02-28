# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class FileFieldOnly(models.FileField):
    """
    如果有同名文件存在, 覆盖它, 而不是默认的重命名自己
    """
    pass
