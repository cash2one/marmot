# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from .models import Role, Profile


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    model = Role
    verbose_name_plural = '角色列表'


# Define an inline admin descriptor for UserCredit model
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = '附加用户信息列表'


# Define a new User admin
class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ('username', 'first_name', 'last_name', 'role', 'email', 'is_staff')
    ordering = ['username']
    list_filter = ('is_staff', 'profile__role__name')

    def role(self, obj):
        return obj.profile.role.name
    role.short_description = '角色'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
