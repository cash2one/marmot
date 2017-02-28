# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import urlparse

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.dispatch import receiver
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from workflow.models import Workflow, WorkflowActivity, WorkflowModelRelation, WorkflowHistory
from workflow.signals import workflow_transitioned
from services.models import IceService, TomcatApp
from springcloud.models import SpringCloudApp


import celerymail


logger = logging.getLogger('marmot')


@receiver(workflow_transitioned)
def auto_send_alert_mail(sender, **kwargs):
    """
    如果task有transition动作被执行, 发邮件提醒
    """
    task = sender.workflowactivity.task
    transition = sender.transition
    from_state = transition.from_state
    to_state = transition.to_state
    participants = sender.workflowactivity.participants.all()  # 参与者

    mail_receivers = set()
    mail_receivers.add(sender.created_by.email)
    for p in participants:
        mail_receivers.add(p.user.email)

    from_state_emails = [u.email for u in from_state.can_view_users() if u.email]
    to_state_emails = [u.email for u in to_state.can_view_users() if u.email]
    for e in from_state_emails:
        mail_receivers.add(e)
    for e in to_state_emails:
        mail_receivers.add(e)

    mail_receivers = filter(lambda x: x, mail_receivers)  # 去除空值

    # 由于运维人员账号公用一个工作邮箱, 所以只当有动作需要运维处理时, 才给ops邮箱发邮件.
    # 平常的进度提醒不用给运维的ops邮箱发
    if 'ops.100credit.com' not in to_state_emails:
        try:
            mail_receivers.remove('ops.100credit.com')
        except ValueError:
            pass

    message = '<h3>{title}</h3>' \
              '<a href="{link}">任务名称： {name}</a>' \
              '<p>任务类型： {type}</p>' \
              '<p>申请人： {applicant}</p>' \
              '<p>当前状态： {state}</p>'\
              '<p>描述： {desc}</p>'\
        .format(
            title='Marmot - 任务提醒',
            name=task.name,
            link=urlparse.urljoin(settings.MAIN_DOMAIN, task.get_absolute_url()),
            type=task.type_raw,
            applicant=task.applicant.get_full_name(),
            state=transition.to_state.name,
            desc=transition.to_state.description
        )

    try:
        celerymail.send_html_mail('Marmot - 任务提醒', message, mail_receivers)
    except Exception:
        logger.exception('Error: Send html mail')


class FirewallGoal(models.Model):
    src_addr = models.CharField(max_length=128, verbose_name='源地址')
    dest_addr = models.CharField(max_length=128, verbose_name='目标地址')
    ports = models.CharField(max_length=128, verbose_name='端口')
    task_firewall = models.ForeignKey('TaskFirewall')


class TaskFirewall(models.Model):
    label = 'firewall'
    label_raw = '开端口任务'

    name = models.CharField(max_length=64, verbose_name='名称')
    note = models.TextField(blank=True, default='', verbose_name='说明')

    tasks = GenericRelation('Task', related_query_name='task_set')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
        verbose_name = '开端口任务'
        verbose_name_plural = '开端口任务列表'


class TaskDNS(models.Model):
    label = 'dns'
    label_raw = '域名解析'

    name = models.CharField(max_length=64, verbose_name='名称')
    domain = models.CharField(max_length=64, blank=True, default='', verbose_name='域名')
    ip = models.GenericIPAddressField(verbose_name='解析地址(IP)')
    note = models.TextField(blank=True, default='', verbose_name='说明')

    tasks = GenericRelation('Task', related_query_name='task_set')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
        verbose_name = '域名解析任务'
        verbose_name_plural = '域名解析任务列表'


class TaskIce(models.Model):
    label = 'ice'
    label_raw = 'Ice任务'

    name = models.CharField(max_length=64, verbose_name='名称')
    ice_app = models.ForeignKey(IceService, verbose_name='Ice应用')
    svn = models.CharField(max_length=128, verbose_name='Svn地址')
    redmine = models.URLField(max_length=255, verbose_name='redmine版本地址')
    note = models.TextField(blank=True, default='', verbose_name='说明')

    tasks = GenericRelation('Task', related_query_name='task_set')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
        verbose_name = 'Ice任务'
        verbose_name_plural = 'Ice任务列表'

    def get_update_url(self):
        return reverse('task_ice_update', kwargs={'pk': self.pk})


class TaskTomcat(models.Model):
    label = 'tomcat'
    label_raw = 'Tomcat任务'

    name = models.CharField(max_length=64, verbose_name='名称')
    tomcat_app = models.ForeignKey(TomcatApp, verbose_name='Tomcat应用')
    svn = models.CharField(max_length=128, verbose_name='Svn地址')
    redmine = models.URLField(max_length=255, verbose_name='redmine版本地址')
    note = models.TextField(blank=True, default='', verbose_name='说明')

    tasks = GenericRelation('Task', related_query_name='task_set')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
        verbose_name = 'Tomcat任务'
        verbose_name_plural = 'Tomcat任务列表'

    def get_update_url(self):
        return reverse('task_tomcat_app_update', kwargs={'pk': self.pk})


class TaskSpringCloud(models.Model):
    label = 'springcloud'
    label_raw = 'SpringCloud任务'

    name = models.CharField(max_length=64, verbose_name='名称')
    app = models.ForeignKey(SpringCloudApp, verbose_name='SpringCloud应用')
    svn = models.CharField(max_length=128, verbose_name='Svn地址')
    redmine = models.URLField(max_length=255, verbose_name='redmine版本地址')
    note = models.TextField(blank=True, default='', verbose_name='说明')

    tasks = GenericRelation('Task', related_query_name='task_set')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
        verbose_name = 'SpringCloud任务'
        verbose_name_plural = 'SpringCloud任务列表'

    def get_update_url(self):
        return reverse('task_springcloud_update', kwargs={'pk': self.pk})


class Task(models.Model):
    workflowactivity = models.OneToOneField(WorkflowActivity, blank=True, null=True)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey(ct_field='content_type', fk_field='object_id')

    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
        verbose_name = '任务'
        verbose_name_plural = '任务列表'
        permissions = (
            ('assign_te', 'Can assign TE'),
            ('progress_transition', 'Make a transition'),
        )

    @property
    def type(self):
        return self.content_type.model_class().label

    @property
    def type_raw(self):
        return self.content_type.model_class().label_raw

    @property
    def is_completed(self):
        return self.get_current_state().is_end_state

    @property
    def name(self):
        return self.content_object.name

    @property
    def note(self):
        return self.content_object.note

    @property
    def applicant(self):
        participant = self.workflowactivity.participants.last()
        if participant:
            return participant.user
        if self.workflowactivity.history.exists():
            return self.workflowactivity.history.last().created_by

    @classmethod
    def create(cls, content, user):
        """添加新任务时, 也要在这里对应的添加"""
        if isinstance(content, TaskFirewall):
            workflow = WorkflowModelRelation.get_workflow(TaskFirewall)
        elif isinstance(content, TaskDNS):
            workflow = WorkflowModelRelation.get_workflow(TaskDNS)
        elif isinstance(content, TaskIce):
            workflow = WorkflowModelRelation.get_workflow(TaskIce)
        elif isinstance(content, TaskTomcat):
            workflow = WorkflowModelRelation.get_workflow(TaskTomcat)
        elif isinstance(content, TaskSpringCloud):
            workflow = WorkflowModelRelation.get_workflow(TaskSpringCloud)
        else:
            raise ValueError('Content is not enabled *Task*')

        if not workflow:
            raise ValueError('WorkflowModelRelation中没有content对应的工作流!')

        workflowactivity = WorkflowActivity(workflow=workflow, created_by=user)
        workflowactivity.save()
        task = cls(workflowactivity=workflowactivity, content_object=content)
        task.save()
        workflowactivity.start(user)
        return task

    def get_current_state(self):
        return self.workflowactivity.current_state

    def get_participants(self):
        return self.workflowactivity.participants.all()

    def get_current_transitions(self):
        """当前state支持的transitions"""
        return self.workflowactivity.current_transitions()

    def has_perm_use_transitions(self, user):
        """当前state下, *user*可以使用的transitions"""
        state = self.get_current_state()
        transitions = self.workflowactivity.workflow.transitions.filter(from_state=state)\
            .filter(Q(users=user) | Q(groups__in=user.groups.all())).all()
        return transitions

    def has_perm_view(self, user):
        """判断*user*是否可以看到此task"""
        if self.workflowactivity.participants.filter(user=user).exists():
            return True
        current_state = self.get_current_state()
        if current_state:
            if current_state.has_perm_view(user):
                return True

    def has_perm_update(self, user):
        """判断*user*是否可以更新此task信息"""
        if user != self.applicant:
            return False
        current_state = self.get_current_state()
        if current_state:
            return current_state.is_updatable
        return False

    def get_type_display(self):
        return self.content_type.model_class().label_raw

    def get_type(self):
        return self.content_type.model_class()

    def get_absolute_url(self):
        return reverse('task_detail', kwargs={'pk': self.pk})

    def get_update_url(self):
        return self.content_object.get_update_url()

    def get_delete_url(self):
        return reverse('task_delete', kwargs={'pk': self.pk})
