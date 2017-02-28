# -*- coding: utf-8 -*-
# from __future__ import unicode_literals, absolute_import
# import os
# from django.db import models
# from django.dispatch import receiver
#
# from .models import IceServiceJar
# from .tasks import download_ice_jar
#
#
# @receiver(models.signals.pre_save, sender=IceServiceJar)
# def auto_add_task_on_change(sender, instance, **kwargs):
#     """
#     Add download-task when corresponding 'IceServiceJar' object is changed.
#     """
#     if instance.pk is None:
#         return False
#     try:
#         old_jar = IceServiceJar.objects.get(pk=instance.pk)
#     except IceServiceJar.DoesNotExist:
#         return False
#
#     new_url = instance.url
#     if old_jar.url != new_url:
#         if os.path.isfile(old_jar.jar.path):
#             os.remove(old_jar.jar.path)
#         download_ice_jar.delay(new_url)
#         old_jar.finished = False
#         old_jar.save()
