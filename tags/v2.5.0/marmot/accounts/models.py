# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User


class Role(models.Model):
    name = models.CharField(max_length=32, verbose_name='名称')
    alias = models.CharField(max_length=32, verbose_name='别名')

    class Meta:
        verbose_name = '角色'
        verbose_name_plural = '角色列表'
        ordering = ['id']

    def __unicode__(self):
        return self.name


class Profile(models.Model):
    PRIVILEGE_CHOICES = (
        (1, '普通'),
        (2, '中级'),
        (3, '高级'),
        (4, '超级'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, verbose_name='角色')
    privilege = models.IntegerField(choices=PRIVILEGE_CHOICES, default=1, verbose_name='权限')
    cell = models.CharField(max_length=40, verbose_name='手机号')

    modify_time = models.DateTimeField(auto_now=True)
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '附加用户信息'
        verbose_name_plural = '附加用户信息列表'
        ordering = ['id']

    def __unicode__(self):
        return 'the extra profile of %s' % self.user.get_full_name()
