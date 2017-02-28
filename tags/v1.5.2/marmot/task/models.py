# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import uuid

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

from django_fsm import FSMIntegerField, transition
from services.models import IceService


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
    note = models.TextField(blank=True, null=True, verbose_name='说明')

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

    @transition(field=state, target=10)
    def submit(self):
        users = Group.objects.get_by_natural_key('senior_cpis').user_set.all()
        for user in users:
            user.email_user(
                'Marmot -- 新任务提醒',
                '',
                settings.EMAIL_HOST_USER,
                html_message=
                '<p>任务名称： {name}</p>'
                '<p>任务类型： {type}</p>'
                '<p>申请人: {applicant}</p>'.format(
                    name=self.name,
                    type=self.get_type_display(),
                    applicant=self.applicant.get_full_name()
                )
            )

    @transition(field=state, source=10, target=20)
    def assign(self, operator):
        self.operator = operator
        self.operator.email_user(
            'Marmot -- 新任务提醒',
            '',
            settings.EMAIL_HOST_USER,
            html_message=
            '<h3>有一个任务指派给你</h3>'
            '<p>任务名称： {name}</p>'
            '<p>任务类型： {type}</p>'
            '<p>申请人: {applicant}</p>'.format(
                name=self.name,
                type=self.get_type_display(),
                applicant=self.applicant.get_full_name()
            )
        )

    @transition(field=state, source=20, target=30)
    def ignore(self):
        self.done = True
        self.applicant.email_user(
            'Marmot -- 任务进度',
            '',
            settings.EMAIL_HOST_USER,
            html_message=
            '<h3>你下面的任务被忽略了</h3>'
            '<p>任务名称： {name}</p>'
            '<p>任务类型： {type}</p>'.format(
                name=self.name,
                type=self.get_type_display(),
            ),
        )

    @transition(field=state, source=20, target=40)
    def over(self):
        self.done = True
        self.applicant.email_user(
            'Marmot -- 任务进度',
            '',
            settings.EMAIL_HOST_USER,
            html_message=
            '<h3>你下面的任务已完成</h3>'
            '<p>任务名称： {name}</p>'
            '<p>任务类型： {type}</p>'.format(
                name=self.name,
                type=self.get_type_display(),
            )
        )

    def get_extra_class(self):
        return self.content_type.model_class()

    def get_extra_obj(self):
        return self.content_object

    def implement(self):
        if isinstance(self.content_object, IceService):
            service = self.content_object
            return service.push_task(self.id)
        else:
            raise TypeError('task type error')

    def get_absolute_url(self):
        return '/task/%s' % self.id

    def get_delete_url(self):
        return '/task/delete/%s' % self.id

    def get_update_url(self):
        return '/task/update/%s' % self.id
