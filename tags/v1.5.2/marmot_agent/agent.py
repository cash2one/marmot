# -*- coding: utf-8 -*-

"""
Marmot Agent
"""

from __future__ import division

import gevent
from gevent import monkey; monkey.patch_all()
from gevent.queue import PriorityQueue

import os
import stat
import json
import urllib
import urllib2
import socket
import signal
import shutil
import zipfile
import argparse
import datetime
import subprocess
import logging
import traceback
from SimpleXMLRPCServer import SimpleXMLRPCServer

import redis

import sysinfo
from monitor import MonitorCpu, MonitorMemory, MonitorDisk, MonitorPort


REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

RDS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')

ICE_PROJECT_DIR = os.path.join(BASE_DIR, 'ice_projects')

if not os.path.exists(SCRIPTS_DIR):
    os.mkdir(SCRIPTS_DIR)

if not os.path.exists(ICE_PROJECT_DIR):
    os.mkdir(ICE_PROJECT_DIR)

logger = logging.Logger('marmot-agent')


def http_get_json(url, param):
    url = url + '?' + urllib.urlencode(param)
    req = urllib2.Request(url)
    res = urllib2.urlopen(req)
    return json.loads(res.read())


def zip_dir(dirname, zipfilename):
    filelist = []
    if os.path.isfile(dirname):
        filelist.append(dirname)
    else:
        for root, dirs, files in os.walk(dirname):
            for d in dirs:
                filelist.append(os.path.join(root, d))
            for f in files:
                filelist.append(os.path.join(root, f))

    zf = zipfile.ZipFile(zipfilename, 'w', zipfile.zlib.DEFLATED)
    for tar in filelist:
        arcname = tar[len(dirname):]
        zf.write(tar, arcname)
    zf.close()
    return zipfilename


def unzip(filename, to_dir):
    if not zipfile.is_zipfile(filename):
        raise ValueError('%s is not zip-file or not exist' % filename)
    if not os.path.exists(to_dir):
        os.mkdir(to_dir)
    zfobj = zipfile.ZipFile(filename)
    for name in zfobj.namelist():
        if name.endswith('/'):
            os.mkdir(os.path.join(to_dir, name))
        else:
            ext_filename = os.path.join(to_dir, name)
            ext_dir = os.path.dirname(ext_filename)
            if not os.path.exists(ext_dir):
                os.makedirs(ext_dir)
            outfile = open(ext_filename, 'wb')
            outfile.write(zfobj.read(name))
            outfile.close()


def backup_dir(dirname):
    dt = datetime.datetime.now().strftime('%y-%m-%d-%H-%M-%S')
    base, name = os.path.split(dirname)
    return zip_dir(dirname, os.path.join(base, 'bak-{0}-{1}.zip'.format(name, dt)))


def clear_dir(dirname):
    for path in os.listdir(dirname):
        filepath = os.path.join(dirname, path)
        if os.path.isfile(filepath):
            os.remove(filepath)
        elif os.path.isdir(filepath):
            shutil.rmtree(filepath, ignore_errors=True)


def exists_file_type(zfile, ft='.jar'):
    zfobj = zipfile.ZipFile(zfile)
    for name in zfobj.namelist():
        if name.endswith(ft):
            return True
    else:
        return False


class XmlRpcServer(SimpleXMLRPCServer):
    allow_client_hosts = []

    def __init__(self, host, port):
        SimpleXMLRPCServer.__init__(self, (host, port), allow_none=True)

    def verify_request(self, request, client_address):
        if self.allow_client_hosts:
            return client_address[0] in self.allow_client_hosts
        else:
            return True


class TaskQueue(PriorityQueue):
    def add_task(self, task, block=True, timeout=None):
        self.put((task.priority, task), block=block, timeout=timeout)

    def pop_task(self, block=True, timeout=None):
        return self.get(block=block, timeout=timeout)[1]


class TaskBase(object):
    def __init__(self, name, identifier, priority):
        self.name = name
        self.identifier = identifier
        self.priority = int(priority)
        RDS.delete(self.identifier)
        RDS.rpush(self.identifier, '*'*16+'Marmot'+'*'*16)
        RDS.rpush(self.identifier, '任务标识: %s' % self.identifier)
        RDS.expire(self.identifier, 60 * 5)

    def header(self):
        return '{} :: '.format(datetime.datetime.now().strftime('%y-%m-%d %H:%M:%S'))

    def log(self, info):
        RDS.rpush(self.identifier, self.header() + info)

    def do(self):
        raise NotImplementedError


class TaskDownloadFile(TaskBase):
    def __init__(self, name, identifier, priority, pkg_url, pkg_dest_path):
        super(TaskDownloadFile, self).__init__(name, identifier, priority)
        self._pkg_url = pkg_url
        self._pkg_dest_path = pkg_dest_path

    def download_file(self):
        filename = os.path.join(ICE_PROJECT_DIR, os.path.basename(self._pkg_url))
        urllib.urlretrieve(self._pkg_url, filename)
        return filename

    def do(self):
        logger.info('Starting to download file: %s ...' % self._pkg_url)
        self.log('Starting to download file: %s ...' % self._pkg_url)
        try:
            filename = self.download_file()
        except IOError as e:
            logger.exception('Download file fail: %s' % self._pkg_url)
            self.log(str(e))
            return
        logger.info('Success to download file: %s' % self._pkg_url)
        self.log('Success to download file: %s' % self._pkg_url)
        return filename


class TaskIceDeploy(TaskDownloadFile):
    def __init__(self, node_name, name, identifier, priority, pkg_url, pkg_dest_path):
        super(TaskIceDeploy, self).__init__(name, identifier, priority, pkg_url, pkg_dest_path)
        self.node_name = node_name.encode('utf-8')

    def header(self):
        return '{0} :: {1} :: '.format(self.node_name, datetime.datetime.now().strftime('%y-%m-%d %H:%M:%S'))

    def wait_syn_file(self):
        self.log('等待文件分发到节点...')
        for i in xrange(60):
            gevent.sleep(1)
            if i >= 5:
                self.log('文件分发完成, 可以启动了')
                break
        else:
            self.log('等待文件分发结果时,超时了')
            raise RuntimeError('Timeout: wait syn file')

    def deploy(self, filename):
        if os.path.exists(self._pkg_dest_path):
            self.log('开始备份旧版本文件...')
            backup_dir(self._pkg_dest_path)
            clear_dir(self._pkg_dest_path)
            self.log('备份完成!')
        else:
            self.log('创建工程目录:%s' % self._pkg_dest_path)
            os.mkdir(self._pkg_dest_path)
        self.log('开始解压zip文件到工程目录...')
        unzip(filename, self._pkg_dest_path)
        self.log('解压zip文件到工程目录--完成')
        self.wait_syn_file()

    def do(self):
        filename = super(TaskIceDeploy, self).do()
        if filename:
            self.deploy(filename)


class TaskCustomScript(TaskBase):
    def __init__(self, name, identifier, priority, script_url):
        super(TaskCustomScript, self).__init__(name, identifier, priority)
        self._script_url = script_url
        self._script_path = os.path.join(SCRIPTS_DIR, os.path.basename(self._script_url))

    def download_script(self):
        urllib.urlretrieve(self._script_url, self._script_path)
        return self._script_path

    def run_script(self):
        os.chmod(self._script_path, stat.S_IRWXU)
        old_dir = os.getcwd()
        os.chdir(SCRIPTS_DIR)
        p = subprocess.Popen(self._script_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.chdir(old_dir)
        return p

    def do(self):
        logger.info('Starting to download script: %s ...' % self._script_url)
        self.log('开始下载脚本: %s ...' % self._script_url)
        try:
            self.download_script()
        except IOError as e:
            logger.error('Download script fail: %s' % self._script_url)
            self.log(str(e))
            return
        else:
            logger.info('Success to download script: %s' % self._script_url)
            self.log('脚本下载完成: %s' % self._script_url)
        self.log('运行脚本...')
        try:
            self.run_script()
        except Exception:
            self.log(traceback.format_exc())
        else:
            self.log('脚本运行成功')


def task_factory(task_info):
    type_ = task_info.pop('type')
    if type_ == 'ice':
        return TaskIceDeploy(
            task_info['node_name'], task_info['name'], task_info['identifier'],
            task_info['priority'], task_info['pkg_url'], task_info['pkg_dest_dir']
        )
    if type_ == 'script':
        return TaskCustomScript(
            task_info['name'], task_info['identifier'], task_info['priority'], task_info['script_url']
        )


class Node(object):
    def __init__(self, ip):
        self._service = None
        self._ip = ip
        self._tasks = TaskQueue()
        self.cpu_monitor = MonitorCpu(self.id)
        self.memory_monitor = MonitorMemory(self.id)
        self.disk_monitor = MonitorDisk(self.id)
        self.port_monitor = MonitorPort(self.id)

    @property
    def id(self):
        return self._ip

    def add_task(self, task):
        self._tasks.add_task(task)

    def get_task_queue(self):
        return self._tasks

    def _create_service(self):
        service = NodeService(self)
        return service

    def get_service(self):
        if not self._service:
            self._service = self._create_service()
        return self._service


class NodeService(object):
    def __init__(self, node):
        self.node = node

    def set_memory_monitor_level(self, level):
        logger.info('Set memory-monitor alarm level: %s' % level)
        self.node.memory_monitor.set_alarm_level(level)

    def set_disk_monitor_level(self, level):
        logger.info('Set disk-monitor alarm level: %s' % level)
        self.node.disk_monitor.set_alarm_level(level)

    def set_allow_ports(self, ports):
        logger.info('Set allow ports: [%s]' % ','.join(ports))
        self.node.port_monitor.set_allow_ports(ports)

    def set_deny_ports(self, ports):
        logger.info('Set deny ports: [%s]' % ','.join(ports))
        self.node.port_monitor.set_deny_ports(ports)

    def set_alarm_interval(self, interval):
        logger.info('Set alarm interval: %s' % interval)
        self.node.cpu_monitor.set_alarm_interval(interval)
        self.node.memory_monitor.set_alarm_interval(interval)
        self.node.disk_monitor.set_alarm_interval(interval)
        self.node.port_monitor.set_alarm_interval(interval)

    def start_monitor(self):
        logger.info('Start monitor...')
        self.node.cpu_monitor.start()
        self.node.memory_monitor.start()
        self.node.disk_monitor.start()
        self.node.port_monitor.start()

    def stop_monitor(self):
        logger.info('Stop monitor...')
        self.node.cpu_monitor.stop()
        self.node.memory_monitor.stop()
        self.node.disk_monitor.stop()
        self.node.port_monitor.stop()

    def add_task(self, task_info):
        logger.info('Add task: %s' % task_info)
        task = task_factory(task_info)
        if task:
            self.node.add_task(task)
            logger.info('Added task: %s' % task.name)

    @staticmethod
    def get_base_info():
        return sysinfo.base_info()

    @staticmethod
    def get_runtime_info():
        return {
            'hostname': socket.gethostname(),
            'users': sysinfo.users(),
            'cpu': sysinfo.cpu(),
            'memory': sysinfo.memory(),
            'swap': sysinfo.swap_memory(),
            'disks': sysinfo.disks(),
        }

    @staticmethod
    def get_processes_info():
        return sysinfo.process_list()


class MarmotAgent(object):
    BIND_HOST = '0.0.0.0'
    PORT = 9001
    SYNC_INTERVAL = 2
    REMOTE_HOST = ''
    CONF_URL = 'http://localhost:8100/assets/server/conf/'
    DEFAULT_CONF = {
        'alarm_url': 'http://localhost:8100/alarm/',
        'monitor': {
            'enabled': False,
            'cpu': 99.0,
            'memory': 80,
            'disk': 80,
            'alarm_interval': 20,
            'allow_ports': [],
            'deny_ports': [],
        }
    }

    @classmethod
    def create_from_cli(cls):
        config = vars(cls.get_args())
        try:
            RDS.keys()
        except redis.RedisError:
            logger.error('Redis: ConnectionError')
            raise
        local_ip = '127.0.0.1' if config['debug'] else sysinfo.get_local_ip()
        if local_ip is None:
            raise IOError('Get local ip error')
        try:
            conf = http_get_json(cls.CONF_URL, {'ip': local_ip})
        except Exception:
            logger.error('Get node config error - %s' % cls.CONF_URL)
            conf = cls.DEFAULT_CONF
        conf['ip'] = local_ip
        config.update(conf)
        return cls(config, RDS)

    @staticmethod
    def get_args():
        parser = argparse.ArgumentParser(
            description='Marmot -- agent'
        )
        parser.add_argument(
            '-b', '--bind',
            action='store',
            dest='host',
            default=None,
            metavar='host',
            help='host to bind default to 0.0.0.0'
        )
        parser.add_argument(
            '-p', '--port',
            action='store',
            type=int,
            dest='port',
            default=None,
            metavar='port',
            help='port to listen default to 9001'
        )
        parser.add_argument(
            '-d', '--debug',
            action='store_true',
            dest='debug',
            default=False,
            help='start agent debug mode'
        )
        return parser.parse_args()

    def __init__(self, config, rds):
        self.config = config
        self.alarm_url = self.config.pop('alarm_url')
        self.monitor_conf = self.config.pop('monitor')
        self._redis = rds
        self._service = Node(self.config.pop('ip')).get_service()
        if self.monitor_conf:
            self._service.set_memory_monitor_level(self.monitor_conf['memory'])
            self._service.set_disk_monitor_level(self.monitor_conf['disk'])
            self._service.set_allow_ports(self.monitor_conf['allow_ports'])
            self._service.set_deny_ports(self.monitor_conf['deny_ports'])
            if self.monitor_conf['enabled']:
                self._service.start_monitor()

    def send_alarm(self, alarm):
        logger.info('Send alarm: %s' % alarm)
        try:
            http_get_json(self.alarm_url, alarm.message())
        except Exception:
            logger.exception('Send alarm error')

    def _monitor_cpu_worker(self, interval):
        logger.info('Starting CPU-Monitor worker...')
        cpu_monitor = self._service.node.cpu_monitor
        while True:
            if cpu_monitor.enabled:
                logger.debug('Monitor CPU worker...')
                alarm = cpu_monitor.has_alarm()
                if alarm:
                    self.send_alarm(alarm)
            gevent.sleep(interval)

    def _monitor_worker(self, interval):
        logger.info('Starting monitor-worker...')
        memory_monitor = self._service.node.memory_monitor
        disk_monitor = self._service.node.disk_monitor
        port_monitor = self._service.node.port_monitor
        while True:
            if memory_monitor.enabled:
                logger.debug('Monitor memory-worker...')
                alarm = memory_monitor.has_alarm()
                if alarm:
                    self.send_alarm(alarm)

            gevent.sleep(0)

            if disk_monitor.enabled:
                logger.debug('Monitor disk-worker...')
                alarm = disk_monitor.has_alarm()
                if alarm:
                    self.send_alarm(alarm)

            gevent.sleep(0)

            if port_monitor.enabled:
                logger.debug('Monitor port-worker...')
                alarm = port_monitor.has_alarm()
                if alarm:
                    self.send_alarm(alarm)
            gevent.sleep(interval)

    def _sync_worker(self, interval):
        logger.info('Starting sync-worker...')
        node_id = self._service.node.id
        while True:
            logger.debug('Sync node info to redis...')
            try:
                self._redis.setex(node_id, 10, json.dumps(self._service.get_runtime_info()))
            except redis.RedisError:
                logger.error('redis error')
            gevent.sleep(interval)

    def _task_worker(self, interval):
        logger.info('Starting task-worker...')
        task_queue = self._service.node.get_task_queue()
        while True:
            if task_queue.empty():
                logger.debug('Waiting task-worker...')
                gevent.sleep(interval)
            else:
                task = task_queue.pop_task()
                logger.info('Starting task: %s' % task.name)
                try:
                    task.do()
                except Exception:
                    logger.exception('task: %s error' % task.name)

    def _setup_workers(self):
        gevent.spawn_later(2, self._monitor_cpu_worker, 2)
        gevent.spawn_later(5, self._monitor_worker, 5)
        gevent.spawn_later(2, self._sync_worker, self.SYNC_INTERVAL)
        gevent.spawn_later(2, self._task_worker, 1)

    def _run_rpc(self):
        host = self.config['host'] or self.BIND_HOST
        port = self.config['port'] or self.PORT
        logger.info('Starting Marmot RPC-Server on %s:%s' % (host, port))
        self.server = XmlRpcServer(host, port)
        self.server.register_instance(self._service)
        self.server.serve_forever()

    def run(self):
        logger.info('Starting Marmot agent...')
        self._setup_workers()
        return self._run_rpc()


def main():
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt='%(asctime)s : %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler('marmot-agent.log', mode='w')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    agent = MarmotAgent.create_from_cli()
    if agent.config['debug']:
        logger.setLevel(logging.DEBUG)
    agent.run()


if __name__ == '__main__':
    gevent.signal(signal.SIGQUIT, gevent.kill)
    main()
