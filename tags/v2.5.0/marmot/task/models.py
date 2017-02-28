# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import uuid

from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

from django_fsm import FSMIntegerField, transition
from services.models import IceService

from utils import send_html_mail


class FirewallGoal(models.Model):
    src_addr = models.CharField(max_length=64, verbose_name='源地址')
    dest_addr = models.CharField(max_length=64, verbose_name='目标地址')
    ports = models.CharField(max_length=128, verbose_name='端口')
    task_firewall = models.ForeignKey('TaskFirewall')


class TaskFirewall(models.Model):
    tasks = generic.GenericRelation('Task', related_query_name='task_set')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '开防火墙任务'
        verbose_name_plural = '开防火墙任务列表'

    @classmethod
    def type(cls):
        return 'firewall'


class Task(models.Model):
    STATE_CHOICE = (
        (10, '待分配'),
        (20, '已分配'),
        (30, '已忽略'),
        (40, '已完成'),
    )
    TASK_CHOICE = {
        'ice': 'ICE服务部署',
        'firewall': '端口开通',
        'tomcat': 'Tomcat应用部署'
    }

    name = models.CharField(max_length=48, verbose_name='名称')
    identifier = models.UUIDField(default=uuid.uuid4, editable=False, verbose_name='任务标识')
    applicant = models.ForeignKey(User, related_name="applicant_task_set", verbose_name='申请人')
    operator = models.ForeignKey(User, blank=True, null=True, related_name="operator_task_set", verbose_name='操作人')
    done = models.BooleanField(default=False, verbose_name='完成')
    deploy = models.BooleanField(default=False, verbose_name='是否支持部署')
    note = models.TextField(blank=True, default='', verbose_name='说明')

    state = FSMIntegerField(choices=STATE_CHOICE, default=10, verbose_name='进度')

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '任务'
        verbose_name_plural = '任务列表'
        permissions = (
            ("implement_task", "Can deploy task"),
            ("assign_task", "Can assign task operator"),
        )

    @property
    def type(self):
        return self.content_type.model_class().type()

    def get_type_display(self):
        return self.TASK_CHOICE[self.type]

    def html_mail_format(self, title, applicant=None, operator=None):
        message = '<h3>{title}</h3>' \
                  '<p>任务名称： {name}</p>' \
                  '<p>任务类型： {type}</p>'.format(title=title, name=self.name, type=self.get_type_display())
        if applicant:
            message += '<p>申请人: %s</p>' % self.applicant.get_full_name()
        if operator:
            message += '<p>操作人: %s</p>' % self.operator.get_full_name()
        return message

    @transition(field=state, target=10)
    def submit(self):
        users = Group.objects.get_by_natural_key('senior_cpis').user_set.all()
        return send_html_mail(
            'Marmot -- 新任务提醒',
            self.html_mail_format('新任务', applicant=True),
            list(set([user.email for user in users]))
        )

    @transition(field=state, source='*', target=20)
    def assign(self, operator):
        self.operator = operator
        return send_html_mail(
            'Marmot -- 新任务提醒',
            self.html_mail_format('有一个任务指派给你', applicant=True),
            [operator.email]
        )

    @transition(field=state, source=20, target=30)
    def ignore(self):
        self.done = True
        return send_html_mail(
            'Marmot -- 任务进度',
            self.html_mail_format('你提的任务被忽略了', operator=True),
            [self.applicant.email]
        )

    @transition(field=state, source=20, target=40)
    def over(self):
        self.done = True
        return send_html_mail(
            'Marmot -- 任务进度',
            self.html_mail_format('你提的任务已完成', operator=True),
            [self.applicant.email]
        )

    def get_extra_class(self):
        return self.content_type.model_class()

    def get_extra_obj(self):
        return self.content_object

    def get_absolute_url(self):
        return '/task/%s' % self.id

    def get_delete_url(self):
        return '/task/delete/%s' % self.id

    def get_update_url(self):
        return '/task/update/%s' % self.id
