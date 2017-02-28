# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import uuid

from django.db import models
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings

from utils.node_proxy import NodeProxy
from assets.models import Server


class Script(models.Model):
    name = models.CharField(max_length=48, unique=True, verbose_name='名称')
    script = models.FileField(upload_to='scripts', verbose_name='脚本文件')
    server = models.ForeignKey(Server, verbose_name='运行位置')
    owner = models.ForeignKey(User, verbose_name='创建人')
    identifier = models.UUIDField(default=uuid.uuid4, editable=False, verbose_name='标识')
    note = models.TextField(blank=True, null=True, verbose_name='描述')

    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '脚本'
        verbose_name_plural = '脚本列表'
        permissions = (
            ("run_script", "Can run script"),
        )

    def __unicode__(self):
        return 'script: %s' % self.name

    def filename(self):
        return os.path.basename(self.script.name)

    def to_task(self):
        return {
            'type': 'script',
            'name': self.name,
            'script_url': settings.MAIN_URL + self.script.url,
        }

    def push_task(self, priority=1):
        """ Push task to node and run """
        node = NodeProxy(self.server.ip, settings.NODE_PORT)
        task_param = self.to_task()
        task_param['identifier'] = self.identifier.get_hex()
        task_param['priority'] = priority
        node.add_task(task_param)

    def get_absolute_url(self):
        return reverse('script_detail', kwargs={'pk': self.pk})

    def get_update_url(self):
        return reverse('script_update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('script_delete', kwargs={'pk': self.pk})


@receiver(models.signals.post_delete, sender=Script)
def auto_delete_script_on_delete(sender, instance, **kwargs):
    """
    Deletes script-file from filesystem
    when corresponding 'Script' object is deleted.
    """
    if instance.script:
        if os.path.isfile(instance.script.path):
            os.remove(instance.script.path)
