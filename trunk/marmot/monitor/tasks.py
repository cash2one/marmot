# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import, division
import re
import json

from django.contrib.auth.models import Group

from celery import current_app as app
from celery.utils.log import get_task_logger
from kazoo.exceptions import NoNodeError
from kazoo.handlers.threading import KazooTimeoutError

from pyalarm.bralarm import send_alarm
from utils import send_html_mail

from .models import (
    RedisClusterMonitor, ESMonitor, Neo4jMonitor,
    HBaseClusterMonitor, IceGridMonitor,
    ActiveMqMonitor, SpringCloudMonitor, KafkaMonitor
)


logger = get_task_logger(__name__)


def send_alarm_to_group(title, content, info='', errcode=41001):
    """
    exceptionCode: [41000 : 41999]
    异常代码定义:
    redis集群错误: 41010
    es错误: 41020
    hbase错误: 41030
    ne04j错误: 41040
    icegrid: 41050
    activemq: 41060
    springcloud: 41070
    kafka: 41080
    """

    logger.info('Get Alarm - %s' % title)

    stat, msg = send_alarm(
        appType='marmot',
        exceptionCode=errcode,
        mailTitle='Marmot -- 警报',
        mailContent='<p>{}</p><p>{}</p><pre>{}</pre>'.format(title, content, info),
        wechatContent=title + '\n' + content + '\n' + '详细信息请查看邮件'
    )
    if not stat:
        logger.error('Alarm send failed: %s msg: %s' % (title, msg))


def send_alarm_to_admins(content):
    users = Group.objects.get_by_natural_key('admins').user_set.all()
    mails = list(set([user.email for user in users]))
    try:
        send_html_mail('Marmot - AdminAlarm', content, mails)
    except Exception:
        logger.exception('Admin email error')


@app.task(name='task.redis_cluster_monitor')
def redis_cluster_monitor():
    rcs = RedisClusterMonitor.objects.filter(active=True).all()
    for rc in rcs:
        info = rc.get_info()
        if info is None:  # 没连上集群
            logger.warning('RedisCluster: %s disconnected; maybe no redis-nodes' % rc.name)
            send_alarm_to_group(
                '警报: "Redis集群: %s"' % rc.name,
                '集群连不上了',
                errcode=41010
            )
            continue

        if info.get('cluster_state') != 'ok':
            logger.warning('RedisCluster: %s - "cluster_state != 0k!"' % rc.name)
            send_alarm_to_group(
                '警报: "Redis集群: %s"' % rc.name,
                'cluster_state != ok !!!',
                json.dumps(info, indent=2),
                errcode=41010
            )
            continue

        if info.get('cluster_slots_fail') != '0':
            logger.warning('RedisCluster: %s - "cluster_slots_fail != 0"' % rc.name)
            send_alarm_to_group(
                '警报: "Redis集群: %s"' % rc.name,
                'cluster_slots_fail != 0 !!!',
                json.dumps(info, indent=2),
                errcode=41010
            )
            continue

        for rn in rc.redisnode_set.all():
            memory_info = rn.get_info(section='memory')
            if memory_info is None:
                logger.warning('RedisNode: %s:%s - disconnected' % (rn.host, rn.port))
                send_alarm_to_group(
                    '警报: "Redis集群: %s"' % rn.cluster.name,
                    'RedisNode: %s:%s - 节点连不上了' % (rn.host, rn.port),
                    errcode=41010,
                )
            else:
                try:
                    used_memory = memory_info.get('used_memory')
                    maxmemory = memory_info.get('maxmemory')
                    if int(used_memory) / int(maxmemory) > 0.95:
                        send_alarm_to_group(
                            '警报: "Redis集群: %s"' % rn.cluster.name,
                            'RedisNode: {}:{} - 内存使用超过了95%'.format(rn.host, rn.port),
                            json.dumps(memory_info, indent=2),
                            errcode=41010
                        )
                except Exception:
                    logger.exception('RedisNode: {}:{} - Memory info Error:\n{}'.format(rn.host, rn.port,
                                                                           json.dumps(memory_info, indent=2)))
    return


@app.task(name='task.es_monitor')
def es_monitor():
    esm_list = ESMonitor.objects.filter(active=True).all()
    for es in esm_list:
        info = es.get_state()
        if info is None:
            logger.warning('ES-Cluster: %s - %s disconnected' % (es.name, es.addr))
            continue
        if info == '':
            logger.warning('ES-Cluster: %s - %s info error' % (es.name, es.addr))
            continue

        status = info.get('status')
        if status == 'green':
            continue
        elif status == 'yellow':
            send_alarm_to_group(
                '警报: "ES集群: %s"' % es.name, 'status: yellow',
                json.dumps(info, indent=2),
                errcode=41020
            )
        elif status == 'red':
            send_alarm_to_group(
                '警报: "ES集群: %s"' % es.name, 'status: red',
                json.dumps(info, indent=2),
                errcode=41020
            )
        else:
            logger.warning('ES-Cluster: %s - %s status: %s error' % (es.name, es.addr, status))
    return


DEAD_SERVERS_PATTERN = re.compile(r'(?P<count>\d+) dead servers')


@app.task(name='task.hbase_monitor')
def hbase_monitor():
    hbc_list = HBaseClusterMonitor.objects.filter(active=True).all()
    for hbc in hbc_list:
        info = hbc.get_info()
        if info is None:
            logger.warning('HBaseCluster: %s - disconnected' % hbc.host)
            continue
        match = re.findall(DEAD_SERVERS_PATTERN, info)
        if match:
            count = match[0]
            if int(count) > 0:
                send_alarm_to_group(
                    '警报: HBaseCluster - %s - %s' % (hbc.name, hbc.host),
                    'dead servers: %s' % count, info, errcode=41030
                )
        else:
            logger.error('HbaseMonitor Error: %s' % info)
    return


@app.task(name='task.neo4j_monitor')
def neo4j_monitor():
    neo4j_list = Neo4jMonitor.objects.filter(active=True).all()
    for neo4j in neo4j_list:
        info = neo4j.get_state()
        if info is None:
            logger.warning('Neo4j: %s disconnected' % neo4j.host)
        elif info == '':
            send_alarm_to_group(
                '警报: Neo4j - %s - %s' % (neo4j.name, neo4j.host),
                '端口: %s 没有被占用' %  neo4j.port, errcode=41040)
        else:
            # SYN-SENT
            if info.count('SYN-SENT') > 5:
                send_alarm_to_group(
                    '警报: Neo4j - %s - %s:%s' % (neo4j.name, neo4j.host, neo4j.port),
                    '端口: %s SYN-SENT 状态的 超过了5个' %  neo4j.port,
                    info, errcode=41040
                )
                continue
            # SYN-RECEIVED
            if info.count('SYN-RECEIVED') > 5:
                send_alarm_to_group(
                    '警报: Neo4j - %s - %s:%s' % (neo4j.name, neo4j.host, neo4j.port),
                    '端口: %s SYN-RECEIVED 状态的 超过了5个' %  neo4j.port,
                    info, errcode=41040
                )
    return


@app.task(name='task.icegrid_monitor')
def icegrid_monitor():
    icegrid_list = IceGridMonitor.objects.filter(active=True).all()
    for icegrid in icegrid_list:
        all_registry_names = icegrid.get_all_registry_names()
        if all_registry_names is None:
            logger.warning('IceGrid: %s disconnected' % icegrid.center.name)
        if icegrid.master not in all_registry_names:
                send_alarm_to_group(
                    '警报: IceGrid - %s' % icegrid.center.name,
                    '主注册: %s 不存在了' % icegrid.master,
                    errcode=41050
                )
        if icegrid.slave not in all_registry_names:
                send_alarm_to_group(
                    '警报: IceGrid - %s' % icegrid.center.name,
                    '从注册: %s 不存在了' % icegrid.slave,
                    errcode=41050
                )

        all_node_names = icegrid.get_all_node_names()
        nodes = icegrid.get_nodes()
        if set(nodes) == set(all_node_names):
            continue

        not_online = [n for n in nodes if n not in all_node_names]
        if not_online:
            send_alarm_to_group(
                '警报 - IceGrid: %s' % icegrid.center.name,
                '节点: %s 不存在了' % not_online,
                errcode=41050
            )
    return


@app.task(name='task.activemq_monitor')
def activemq_monitor():
    activemq_monitor_list = ActiveMqMonitor.objects.filter(active=True).all()

    for monitor in activemq_monitor_list:
        try:
            queues_info = monitor.get_queues_info()
        except IOError:
            send_alarm_to_group(
                '警报 - AcitveMQ: %s' % monitor.name,
                '监控接口无法访问, 请检查集群是否宕机',
                errcode=41060
            )
            continue
        except ValueError:
            send_alarm_to_group(
                '警报 - AcitveMQ: %s' % monitor.name,
                '请检查监控接口的地址和用户名密码是否有误',
                errcode=41060
            )
            continue

        level = monitor.level
        for qinfo in queues_info:
            if qinfo['QueueSize'] > level:
                send_alarm_to_group(
                    '警报 - AcitveMQ: %s' % monitor.name,
                    '队列[%s]等待消息已经超过警报线: %s' % (qinfo['QueueName'], qinfo['QueueSize']),
                    info=json.dumps(qinfo, indent=4), errcode=41060
                )


@app.task(name='task.springcloud_monitor')
def springcloud_monitor():
    springcloud_monitor_list = SpringCloudMonitor.objects.filter(active=True).all()
    for monitor in springcloud_monitor_list:
        if not monitor.ping():
            send_alarm_to_group(
                '警报 - SpringCloud: %s - %s:%s' % (monitor.name, monitor.addr, monitor.port),
                '监控接口无法访问, 请检查服务是否正常!', errcode=41070
            )


@app.task(name='task.kafka_monitor')
def kafka_monitor():
    kafka_monitor_list = KafkaMonitor.objects.filter(active=True).all()
    for monitor in kafka_monitor_list:
        try:
            monitor.create_zk()
        except KazooTimeoutError:
            send_alarm_to_group(
                '警报 - Kafka: %s - %s' % (monitor.name, monitor.addr),
                'Zookeeper无法连接, 请检查服务是否正常!', errcode=41080
            )
            continue

        try:
            ids = monitor.get_ids()
            topics = monitor.get_topics()
        except NoNodeError as e:
            send_alarm_to_group(
                '警报 - Kafka: %s - %s' % (monitor.name, monitor.addr),
                'Zookeeper访问异常: %s' % str(e), errcode=41081
            )
            continue
        finally:
            monitor.destroy_zk()

        if ids != monitor.ids.split(','):
            send_alarm_to_group(
                '警报 - Kafka: %s - %s' % (monitor.name, monitor.addr),
                'ids异常: %s' % ids, errcode=41082
            )
            continue

        for k, vs in topics.items():
            for v in vs:
                if set(v['replicas']) != set(v['isr']):
                    send_alarm_to_group(
                        '警报 - Kafka: %s - topic: %s' % (monitor.name, k),
                        'zookeeper地址: %s - Replicas: %s != Isr: %s' % (monitor.addr, v['replicas'], v['isr']),
                        errcode=41084
                    )
                    continue

                if len(v['replicas']) < monitor.replicas:
                    send_alarm_to_group(
                        '警报 - Kafka: %s - topic: %s' % (monitor.name, k),
                        'zookeeper地址: %s - replicas: %s 小于 %s' % (monitor.addr, v['replicas'], monitor.replicas),
                        errcode=41085
                    )

                if len(v['isr']) < monitor.isr:
                    send_alarm_to_group(
                        '警报 - Kafka: %s - topic: %s' % (monitor.name, k),
                        'zookeeper地址: %s - isr: %s 小于 %s' % (monitor.addr, v['isr'], monitor.isr),
                        errcode=41086
                    )
                    continue

                # 下面的判断条件有待商确
                if v['leader'] is None or v['leader'] == 'null' or v['leader'] == '':
                    send_alarm_to_group(
                        '警报 - Kafka: %s - topic: %s' % (monitor.name, k),
                        'zookeeper地址: %s - leader异常: %s' % (monitor.addr, v['leader']),
                        errcode=41083
                    )
