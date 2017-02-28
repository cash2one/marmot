# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import uuid

from django.db import models
from django.contrib.auth.models import User

from services.models import IceService


class TaskFirewall(models.Model):
    src_addr = models.CharField(max_length=128, verbose_name='源地址')
    dest_addr = models.CharField(max_length=128, verbose_name='目标地址')
    ports = models.CharField(max_length=128, verbose_name='端口')

    class Meta:
        verbose_name = '开防火墙任务'
        verbose_name_plural = '开防火墙任务列表'


class Task(models.Model):
    PROGRESS_CHOICE = (
        (10, '待分配'),
        (20, '已分配'),
        (30, '已忽略'),
        (40, '已完成'),
    )
    TASK_CHOICE = (
        ('ice', 'ICE服务部署'),
        ('firewall', '端口开通'),
    )
    EXTRA_MAP = {
        'ice': IceService,
        'firewall': TaskFirewall,
    }

    name = models.CharField(max_length=48, verbose_name='名称')
    identifier = models.UUIDField(default=uuid.uuid4, editable=False, verbose_name='任务标识')
    applicant = models.ForeignKey(User, related_name="applicant_task_set", verbose_name='申请人')
    operator = models.ForeignKey(User, blank=True, null=True, related_name="operator_task_set", verbose_name='操作人')
    type = models.CharField(max_length=24, choices=TASK_CHOICE, verbose_name='任务类型')
    extra_id = models.PositiveIntegerField(verbose_name='外联表id')
    progress = models.IntegerField(choices=PROGRESS_CHOICE, default=10, verbose_name='进度')
    done = models.BooleanField(default=False, verbose_name='完成')
    deploy = models.BooleanField(default=False, verbose_name='是否支持部署')
    note = models.TextField(blank=True, null=True, verbose_name='说明')

    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '任务'
        verbose_name_plural = '任务列表'
        permissions = (
            ("implement_task", "Can deploy task"),
            ("assign_task", "Can assign task operator"),
        )

    def get_absolute_url(self):
        return '/task/%s' % self.id

    def get_delete_url(self):
        return '/task/delete/%s' % self.id

    def get_update_url(self):
        return '/task/update/%s' % self.id

    def get_extra_class(self):
        return self.EXTRA_MAP[self.type]

    def get_extra_obj(self):
        return self.get_extra_class().objects.get(id=self.extra_id)

    def implement(self):
        if self.type == 'ice':
            service = self.get_extra_obj()
            return service.push_task(self.id)
        else:
            raise TypeError('task type error %s' % self.type)
