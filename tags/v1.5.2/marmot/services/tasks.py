# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
import os
import urllib

from django.core.files import File
from django.utils.text import get_valid_filename
from celery import current_app as app
from celery.utils.log import get_task_logger

from utils import backup_database, execute_sql
from .models import IceServiceJar, TomcatAppWar, TomcatAppSql, TomcatApp


logger = get_task_logger(__name__)


@app.task(name='task.download_ice_jar')
def download_ice_jar(url, identifier):
    basename = os.path.basename(url)
    filename = os.path.join('/tmp/', get_valid_filename(basename))
    try:
        jar = IceServiceJar.objects.get(id=identifier)
    except IceServiceJar.DoesNotExist:
        logger.exception('IceServiceJar: %s does not exists' % identifier)
        return False
    try:
        urllib.urlretrieve(url, filename)
    except IOError:
        logger.exception('download error - %s' % url)
    logger.info('download succeed - %s' % url)
    f = open(filename)
    jar.package.save(basename, File(f))
    f.close()
    jar.finished = True
    jar.save()


@app.task(name='task.download_war')
def download_war(url, identifier):
    basename = os.path.basename(url)
    filename = os.path.join('/tmp/', get_valid_filename(basename))
    try:
        war = TomcatAppWar.objects.get(id=identifier)
    except TomcatAppWar.DoesNotExist:
        logger.exception('TomcatAppWar: %s does not exists' % identifier)
        return False
    try:
        urllib.urlretrieve(url, filename)
    except IOError:
        logger.exception('download error - %s' % url)
    logger.info('download succeed - %s' % url)
    f = open(filename)
    war.package.save(basename, File(f))
    f.close()
    war.state = 2  # 就绪
    war.save()


@app.task(name='task.backup_db')
def task_backup_db(tomcat_app_id):
    try:
        app = TomcatApp.objects.get(pk=tomcat_app_id)
    except TomcatApp.DoesNotExist:
        logger.error('TomcatApp: %s does not exists' % tomcat_app_id)
        return False
    try:
        bak_file = backup_database(app.db_ip, app.db_port, app.db_user, app.db_pwd, app.db_name)
    except RuntimeError:
        logger.error('backup database: %s error' % app.db_name)
        return False
    else:
        f = open(bak_file)
        tomcat_sql = TomcatAppSql(note='系统备份', tomcat_app=app, sys_bak=True)
        tomcat_sql.sql.save(os.path.basename(bak_file), File(f))
        f.close()
        tomcat_sql.save()
        return True
    finally:
        app.bak_flag = False
        app.save()


@app.task(name='task.execute_sql')
def task_execute_sql(pk):
    try:
        sql = TomcatAppSql.objects.get(pk=pk)
    except TomcatAppSql.DoesNotExist:
        logger.error('TomcatAppSql: %s done not exists!' % pk)
        return False
    if sql.tomcat_app.bak_flag:
        logger.error('系统正在备份Tomcat应用 "%s" 的数据库, 暂时不能执行sql' % sql.tomcat_app.name)
    else:
        if not os.path.isfile(sql.sql.path):
            logger.error('sql文件: %s 不存在!' % sql.sql.name)
        else:
            ret = execute_sql(sql.tomcat_app.db_ip, sql.tomcat_app.db_port, sql.tomcat_app.db_user,
                              sql.tomcat_app.db_pwd, sql.tomcat_app.db_name, sql.sql.path)
            if ret != 0:
                logger.error('sql文件: %s 执行错误!' % sql.sql.path)
    sql.state = 1  # 空闲
    sql.save()
    return True
