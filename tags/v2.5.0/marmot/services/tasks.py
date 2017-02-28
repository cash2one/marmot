# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
import os
import urllib

from django.core.files import File
from django.utils.text import get_valid_filename
from celery import current_app as app
from celery.utils.log import get_task_logger

from utils import backup_database, execute_sql
from .models import IceServiceJar, TomcatAppWar, TomcatAppSql, TomcatAppDB


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
        jar.state = 3  # 下载失败
        jar.save()
        return False
    else:
        logger.info('download succeed - %s' % url)
        f = open(filename)
        jar.package.save(basename, File(f))
        f.close()
        jar.state = 2  # 下载完成
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
        war.state = 3  # 下载失败
        war.save()
        return False
    else:
        logger.info('download succeed - %s' % url)
        f = open(filename)
        war.package.save(basename, File(f))
        f.close()
        war.state = 2  # 就绪
        war.save()


@app.task(name='task.backup_db')
def task_backup_db(db_id):
    try:
        db = TomcatAppDB.objects.get(pk=db_id)
    except TomcatAppDB.DoesNotExist:
        return False
    try:
        bak_file = backup_database(db.ip, db.port, db.user, db.pwd, db.name)
    except RuntimeError:
        logger.exception('backup database: %s error' % db.name)
        return False
    else:
        f = open(bak_file)
        tomcat_sql = TomcatAppSql(note='系统备份', db=db, tomcat_app=db.app, sys_bak=True)
        tomcat_sql.sql.save(os.path.basename(bak_file), File(f))
        f.close()
        tomcat_sql.save()
        return True
    finally:
        db.state = 1  # 空闲
        db.save()


@app.task(name='task.execute_sql')
def task_execute_sql(sql_id):
    try:
        sql = TomcatAppSql.objects.get(pk=sql_id)
    except TomcatAppSql.DoesNotExist:
        return False
    ret = execute_sql(sql.db.ip, sql.db.port, sql.db.user, sql.db.pwd, sql.db.name, sql.sql.path)
    if ret != 0:
        logger.error('sql文件: %s 执行错误!' % sql.sql.path)
    sql.state = 1  # 空闲
    sql.save()
    db = sql.db
    db.state = 1  # 空闲
    db.save()
    return True
