# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import datetime

from django.db import models
from django.utils.encoding import force_str, force_text


class FileFieldOnly(models.FileField):
    """
    将spingcloud的app文件按照lib; lib/libs; config来存储
    """

    def get_directory_name(self):
        return os.path.normpath(force_text(datetime.datetime.now().strftime(force_str(self.upload_to))))

    def get_filename(self, filename):
        return os.path.normpath(os.path.basename(filename))

    def generate_filename(self, instance, filename):
        app_name = instance.app.name
        cluster_name = instance.app.cluster.name
        _type = instance.type
        if _type == 0:
            return 'springcloud/{0}/{1}/lib/{2}'.format(cluster_name, app_name, filename)
        elif _type == 1:
            return 'springcloud/{0}/{1}/lib/libs/{2}'.format(cluster_name, app_name, filename)
        elif _type == 2:
            return 'springcloud/{0}/{1}/config/{2}'.format(cluster_name, app_name, filename)
        else:
            raise ValueError('SpringCloudFile - type: %s ERROR!' % _type)
