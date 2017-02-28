#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division

import gevent
from gevent import monkey; monkey.patch_all()
from gevent.queue import PriorityQueue
from gevent import subprocess

import os
import platform
import time
import datetime
import socket
import fcntl
import struct
import subprocess
import re
import json
import shutil
import urllib
import urllib2
import zipfile
import stat
import signal
import logging
import argparse
import traceback
from array import array
from SimpleXMLRPCServer import SimpleXMLRPCServer

import redis
import psutil
import netifaces


# **********************************************************************************
# 配置
# **********************************************************************************


CONF_URL = 'http://192.168.23.115:8100/assets/server/conf/'

DEFAULT_CONF = {
    'alarm_url': 'http://192.168.23.115:8100/alarm/',
    'monitor': {
        'enabled': False,
        'cpu': 99.0,
        'memory': 80,
        'disk': 80,
        'alarm_interval': 20,
    }
}

IFNAME = 'eth0'  # 使用哪个网卡地址

REDIS_HOST = '192.168.23.115'
REDIS_PORT = 6379
REDIS_DB = 0
RDS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
if not os.path.exists(SCRIPTS_DIR):
    os.mkdir(SCRIPTS_DIR)

ICE_PROJECT_DIR = '/tmp'
TOMCAT_DIR = '/tmp'


logger = logging.Logger('marmot-agent')
LOG_File = 'marmot-agent.log'


# **********************************************************************************
# 获取机器的静态信息
# **********************************************************************************


def dmidecode_system():
    system_pattern = re.compile(
        r'System\ Information\n\tManufacturer:\ (?P<manufacturer>.*)\n'
        r'\tProduct\ Name:\ (?P<product_name>.*)\n'
        r'\tVersion:\ (?P<version>.*)\n'
        r'\tSerial\ Number:\ (?P<serial_number>.*)\n'
        r'\tUUID:\ (?P<uuid>.*)\n'
        r'\t(.)*\n'
        r'\t(.)*\n'
        r'\tFamily:\ (?P<family>.*)\n'
    )
    content = subprocess.check_output(['sudo', 'dmidecode'])
    match = re.search(system_pattern, content)
    return {
        'manufacturer': match.group('manufacturer'),
        'product-name': match.group('product_name'),
        'version': match.group('version'),
        'serial-number': match.group('serial_number'),
        'uuid': match.group('uuid'),
        'family:': match.group('family'),
    }


def cpu_info():
    vendor_pattern = re.compile(r'vendor_id([\ \t])+\:\ (?P<vendor_id>.*)\n')
    model_pattern = re.compile(r'model\ name([\ \t])+\:\ (?P<model_name>.*)\n')
    f = open('/proc/cpuinfo')
    content = f.read()
    f.close()
    return {
        'vendor': re.search(vendor_pattern, content).group('vendor_id').strip(),
        'model': re.search(model_pattern, content).group('model_name').strip(),
        'core_num': psutil.cpu_count(logical=True),  # logical
    }


def get_hwaddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
    return ':'.join(['%02x' % ord(char) for char in info[18:24]])


def netcard_info():
    interfaces = netifaces.interfaces()
    if 'lo' in interfaces:
        interfaces.remove('lo')
    ret = {}
    for i in interfaces:
        try:
            netcard = netifaces.ifaddresses(i)[netifaces.AF_INET][0]
        except KeyError:
            continue

        ret[i] = {
            'mac': get_hwaddr(i),
            'broadcast': netcard['broadcast'],
            'mask': netcard['netmask'],
            'addr': netcard['addr'],
        }
    return ret


def socket_constants(prefix):
    return dict((getattr(socket, n), n) for n in dir(socket) if n.startswith(prefix))


SOCKET_FAMILIES = socket_constants('AF_')
SOCKET_TYPES = socket_constants('SOCK_')


def get_local_ip(ifname='eth0'):
    addrs = {}
    for iface_name in netifaces.interfaces():
        addresses = [i['addr'] for i in netifaces.ifaddresses(iface_name).setdefault(netifaces.AF_INET, [{'addr': None}])]
        addrs[iface_name] = addresses[0]
    return addrs[ifname]


def base_info():
    return {
        'hostname': socket.gethostname(),
        'system': dmidecode_system(),
        'os_distribution': '-'.join(platform.linux_distribution()),
        'os_verbose': platform.platform(),
        'cpu_info': cpu_info(),
        'disk_size': '%sG' % disk_total()['total'],
        'memory_total': memory()['total'],
    }


# **********************************************************************************
# 机器的runtime信息
# **********************************************************************************


def users():
    user_list = []
    for u in psutil.users():
        user_list.append({
            'name': u.name,
            'terminal': u.terminal,
            'host': u.host,
            'started': datetime.datetime.fromtimestamp(u.started).strftime('%Y-%m-%d %H:%M:%S'),
        })
    return user_list


def memory():
    data = psutil.virtual_memory()
    divisor = 1024**3
    return {
        'total': '%.2fG' % (data.total/divisor),
        'available': '%.2fG' % (data.available/divisor),
        'used': '%.2fG' % (data.used/divisor),
        'free': '%.2fG' % (data.free/divisor),
        'percent': '{}%'.format(data.percent),
        'active': '%.2fG' % (data.active/divisor),
        'inactive': '%.2fG' % (data.inactive/divisor),
        'buffers': '%.2fG' % (data.buffers/divisor),
        'cached': '%.2fG' % (data.cached/divisor),
    }


def swap_memory():
    sm = psutil.swap_memory()
    divisor = 1024 ** 3
    return {
        'total': '%.2fG' % (sm.total/divisor),
        'free': '%.2fG' % (sm.free/divisor),
        'used': '%.2fG' % (sm.used/divisor),
        'percent': '{}%'.format(sm.percent),
        'swapped_in': sm.sin/divisor,
        'swapped_out': sm.sout/divisor,
    }


def cpu():
    cpu_times = psutil.cpu_times_percent(0)
    return {
        'user': cpu_times.user,
        'system': cpu_times.system,
        'idle': cpu_times.idle,
        'iowait': cpu_times.iowait,
        'load_avg': os.getloadavg(),
    }


def disk_total():
    disk_data = disks(all_partitions=True)
    space_total = round(sum([i['total'] for i in disk_data]), 2)
    space_used = round(sum([i['used'] for i in disk_data]), 2)
    return {
        'total': space_total,
        'used': space_used,
        'free': round(sum([i['free'] for i in disk_data]), 2),
        'percent': round((space_used/space_total)*100, 2),
    }


def disks(all_partitions=False):
    divisor = 1024**3
    dks = []
    for dp in psutil.disk_partitions(all_partitions):
        usage = psutil.disk_usage(dp.mountpoint)
        disk = {
            'device': dp.device,
            'mountpoint': dp.mountpoint,
            'type': dp.fstype,
            'options': dp.opts,
            'total': round((usage.total/divisor), 2),
            'used': round((usage.used/divisor), 2),
            'free': round((usage.free/divisor), 2),
            'percent': usage.percent,
        }
        dks.append(disk)
    return dks


def disks_counters(perdisk=True):
    return {dev: c._asdict() for dev, c in psutil.disk_io_counters(perdisk=perdisk).iteritems()}


def net_io_counters():
    return psutil.net_io_counters()._asdict()


def net_connections():
    return psutil.net_connections()


def process_list():
    p_list = []
    for p in psutil.process_iter():
        mem = p.memory_info()
        # psutil throws a KeyError when the uid of a process is not associated with an user.
        try:
            username = p.username()
        except KeyError:
            username = None

        proc = {
            'pid': p.pid,
            'name': p.name(),
            'cmdline': ' '.join(p.cmdline()),
            'user': username,
            'status': p.status(),
            'created': p.create_time(),
            'mem_rss': mem.rss,
            'mem_vms': mem.vms,
            'mem_percent': p.memory_percent(),
            'cpu_percent': p.cpu_percent(0)
        }
        p_list.append(proc)

    return p_list


def connections(filters=None):
    filters = filters or {}
    conns = []
    for c in psutil.net_connections('all'):
        conn = {
            'fd': c.fd,
            'pid': c.pid,
            'family': SOCKET_FAMILIES[c.family],
            'type': SOCKET_TYPES[c.type],
            'local_addr_host': c.laddr[0] if c.laddr else None,
            'local_addr_port': c.laddr[1] if c.laddr else None,
            'remote_addr_host': c.raddr[0] if c.raddr else None,
            'remote_addr_port': c.raddr[1] if c.raddr else None,
            'state': c.status
        }
        for k, v in filters.iteritems():
            if v and conn.get(k) != v:
                break
        else:
            conns.append(conn)
    return conns


def listening_port_set():
    ports = set()
    for c in psutil.net_connections('all'):
        if c.laddr:
            port = c.laddr[1]
            if isinstance(port, int):
                ports.add(port)
    return ports


# **********************************************************************************
# Monitor
# **********************************************************************************


class Alarm(object):
    """
    警报级别 - level: 1(一般), 2(中级), 3(严重)
    警报类型 - type: cpu, memory, disk, port
    """
    def __init__(self, host, level, type_, msg):
        self.host = host
        self.level = level
        self.type = type_
        self.msg = msg

    def message(self):
        return {
            'host': self.host,
            'level': self.level,
            'type': self.type,
            'msg': self.msg,
        }

    def __str__(self):
        return str(self.message())


class Buffer(object):
    def __init__(self, size, atype='f'):
        self.atype = atype
        self.size = size
        self.items = array(atype, [])

    def size(self):
        return len(self.items)

    def append(self, item):
        if len(self.items) >= self.size:
            del self.items[0]
        self.items.append(item)

    def pre_items(self, x):
        return self.items[0:x].tolist()

    def xmean(self, x):
        return sum(self.items[0:x]) / x

    def preview(self):
        return self.items.tolist()

    def flush(self):
        self.items = array(self.atype, [])

    def mean(self):
        return sum(self.items) / len(self.items)

    def sum(self):
        return sum(self.items)


class Timer(object):
    def __init__(self, interval):
        self._interval = interval  # second
        self.st = time.time()

    def set_interval(self, interval):
        self._interval = interval

    def update(self):
        self.st = time.time()
        return self.st

    def done(self):
        now = time.time()
        if (now - self.st) >= self._interval:
            self.st = now
            return True
        else:
            return False


class BaseMonitor(object):
    def __init__(self, host, alarm_interval=20):
        self.host = host
        self.enabled = False
        self.alarm_countor = 0
        self.alarm_timer = Timer(60*alarm_interval)

    def reset_alarm_countor(self):
        self.alarm_countor = 0

    def increase_alarm_countor(self):
        self.alarm_countor += 1

    def set_alarm_interval(self, interval):
        """
        :param interval: Minutes
        """
        self.alarm_timer.set_interval(60*interval)

    def start(self):
        self.enabled = True

    def stop(self):
        self.enabled = False

    def get_alarm(self):
        raise NotImplementedError

    def has_alarm(self):
        if not self.enabled:
            return
        alarm = self.get_alarm()
        if alarm:
            if self.alarm_countor:
                if self.alarm_timer.done():
                    return alarm
                else:
                    return
            else:
                self.increase_alarm_countor()
                self.alarm_timer.update()
                return alarm
        else:
            self.alarm_timer.update()
            self.reset_alarm_countor()


class MonitorCpu(BaseMonitor):
    """
    Cpu负载监视器
    """
    def __init__(self, host, alarm_interval=20):
        super(MonitorCpu, self).__init__(host, alarm_interval=alarm_interval)
        # 监控worker的interval是2second, 这里缓冲1个小时的数据, 即1800个数据
        self.buf = Buffer(1800)

    def load_avg(self):
        self.buf.append(psutil.cpu_percent())  # 刷新缓冲
        return {
            'avg10': self.buf.xmean(10*30),
            'avg30': self.buf.xmean(30*30),
            'avg60': self.buf.xmean(60*30),
        }

    def get_alarm(self):
        avg = self.load_avg()
        if avg['avg60'] >= 99.0:
            return Alarm(self.host, 3, 'cpu', '{}: Cpu负载已经持续1小时超过99%'.format(self.host))
        if avg['avg30'] >= 99.0:
            return Alarm(self.host, 2, 'cpu', '{}: Cpu负载已经持续30分钟超过99%'.format(self.host))
        if avg['avg10'] >= 99.0:
            return Alarm(self.host, 1, 'cpu', '{}: Cpu负载已经持续10分钟超过99%'.format(self.host))


class MonitorMemory(BaseMonitor):
    """
    Memory监视器
    """
    def __init__(self, host, level=80, alarm_interval=20):
        super(MonitorMemory, self).__init__(host, alarm_interval=alarm_interval)
        self._alarm_level = level
        self.buf = Buffer(12)

    def set_alarm_level(self, level):
        self._alarm_level = level

    def get_alarm(self):
        self.buf.append(psutil.virtual_memory().percent)
        used = self.buf.mean()
        if used >= self._alarm_level:
            return Alarm(self.host, 2, 'memory', '{0}: 内存使用已经达到{1}%'.format(self.host, used))


class MonitorDisk(MonitorMemory):
    """
    Disk监视器
    """
    def get_alarm(self):
        for disk in disks():
            if disk['percent'] >= self._alarm_level:
                return Alarm(
                    self.host, 2, 'disk',
                    '{0}: 硬盘挂载点: {1}, 使用已经达到{2}%'.format(self.host, disk['mountpoint'], disk['percent'])
                )


class MonitorPort(BaseMonitor):
    """
    Port监视器
    """
    def __init__(self, host, alarm_interval=20):
        super(MonitorPort, self).__init__(host, alarm_interval=alarm_interval)
        self.allow_ports = set()  # 监听的端口
        self.deny_ports = set()  # 开放的端口 - 不允许被占用

    def set_allow_ports(self, ports):
        self.allow_ports = set(ports)

    def set_deny_ports(self, ports):
        self.deny_ports = set(ports)

    def get_alarm(self):
        listening_ports = listening_port_set()

        if self.allow_ports:
            if not (self.allow_ports < listening_ports):
                not_ports = self.allow_ports - listening_ports  # 监控端口列表中,没有被listen的端口
                return Alarm(self.host, 2, 'port', '{0}: 监听端口{1}没有被监听'.format(self.host, not_ports))

        if self.deny_ports:
            tmp = self.deny_ports & listening_ports
            if tmp:
                return Alarm(self.host, 2, 'port', '{0}: 开放端口{1}被占用'.format(self.host, tmp))


# **********************************************************************************
# Marmot
# **********************************************************************************


def http_get_json(url, param):
    url = url + '?' + urllib.urlencode(param)
    req = urllib2.Request(url)
    res = urllib2.urlopen(req)
    return json.loads(res.read())


def zip_dir(dirname, zipfilename=None):
    if zipfilename is None:
        zipfilename = os.path.basename(os.path.normpath(dirname)) + '.zip'
    zipf = zipfile.ZipFile(zipfilename, 'w', zipfile.ZIP_DEFLATED, allowZip64=True)
    base_len = len(dirname)
    for root, dirs, files in os.walk(dirname):
        for f in files:
            fn = os.path.join(root, f)
            zipf.write(fn, fn[base_len:])
        for d in dirs:
            fn = os.path.join(root, d)
            zipf.write(fn, fn[base_len:])
    zipf.close()


def unzip(filename, to_dir):
    zip_ref = zipfile.ZipFile(filename, 'r')
    zip_ref.extractall(to_dir)
    zip_ref.close()


def backup_dir(dirname):
    dt = time.strftime('%Y-%m-%d-%H-%M-%S')
    base, name = os.path.split(dirname)
    bak_dir = os.path.join(base, 'bak')
    if not os.path.exists(bak_dir):
        os.mkdir(bak_dir)
    return zip_dir(dirname, os.path.join(bak_dir, 'bak-{0}-{1}.zip'.format(name, dt)))


def clear_dir(dirname):
    for path in os.listdir(dirname):
        filepath = os.path.join(dirname, path)
        if os.path.isfile(filepath):
            os.remove(filepath)
        elif os.path.isdir(filepath):
            shutil.rmtree(filepath, ignore_errors=True)


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
        logger.info('Received Task: %s uuid: %s ...' % (name, identifier))
        self.name = name
        self.identifier = identifier
        self.priority = int(priority)
        RDS.delete(self.identifier)
        RDS.rpush(self.identifier, ' * '*16 + ' Marmot ' + ' * '*16)
        RDS.rpush(self.identifier, '任务标识: %s' % self.identifier)
        RDS.expire(self.identifier, 60 * 5)

    def header(self):
        return '{} :: '.format(time.strftime('%Y-%m-%d %H:%M:%S'))

    def log(self, info):
        RDS.rpush(self.identifier, self.header() + info)

    def do(self):
        raise NotImplementedError


class DownloadMixin(object):
    def callback_progress(self, blocknum, blocksize, totalsize):
        percent = 100.0 * blocknum * blocksize / totalsize
        if percent > 100:
            percent = 100
        self.log('%.2f%%' % percent)

    def download_file(self, url, to_dir, fname=None):
        filename = os.path.join(to_dir, os.path.basename(url) if fname is None else fname)
        logger.info('Starting to download file: %s ...' % url)
        self.log('开始下载文件: %s ...' % url)
        try:
            urllib.urlretrieve(url, filename)
        except IOError as e:
            logger.exception('Download file fail: %s' % url)
            self.log(str(e))
            return
        logger.info('Success to download file: %s' % url)
        self.log('下载完成: %s' % url)
        return filename


class TaskIceDeploy(DownloadMixin, TaskBase):
    def __init__(self, node_name, service_name, identifier, priority, jar, conf, pkg_dest_path):
        super(TaskIceDeploy, self).__init__(service_name, identifier, priority)
        self.node_name = node_name.encode('utf-8')
        self.jar = jar
        self.conf = conf
        self._pkg_dest_path = pkg_dest_path

    def header(self):
        return '{0} :: {1} :: '.format(self.node_name, time.strftime('%Y-%m-%d %H:%M:%S'))

    def download_jar(self):
        if self.jar:
            return self.download_file(self.jar, ICE_PROJECT_DIR)

    def download_conf(self):
        if self.conf:
            return self.download_file(self.conf, ICE_PROJECT_DIR)

    def deploy(self, jar, conf):
        if os.path.exists(self._pkg_dest_path):
            self.log('开始备份旧版本文件...')
            backup_dir(self._pkg_dest_path)
            clear_dir(self._pkg_dest_path)
            self.log('备份完成!')
        else:
            self.log('创建工程目录: %s' % self._pkg_dest_path)
            os.makedirs(self._pkg_dest_path)
        self.log('处理lib和config文件 ...')
        lib_path = os.path.join(self._pkg_dest_path, 'lib')
        os.mkdir(lib_path)
        shutil.move(jar, lib_path)
        if conf:
            # config_path = os.path.join(self._pkg_dest_path, 'config')
            # os.mkdir(config_path)
            unzip(conf, self._pkg_dest_path)
        self.log('处理完成...')
        self.log('>>>>>>>>>>>>>>>>完成<<<<<<<<<<<<<<<<<<')

    def do(self):
        jar = self.download_jar()
        conf = self.download_conf()
        if jar:
            self.deploy(jar, conf)
        else:
            self.log('jar包地址有误, 部署失败')


class TaskTomcatWar(DownloadMixin, TaskBase):
    def __init__(self, host, app_name, identifier, priority, war_url, war_dir):
        super(TaskTomcatWar, self).__init__(app_name, identifier, priority)
        self.host = host
        self.war_url = war_url
        self.war_dir = war_dir

    def header(self):
        return '{0} :: {1} :: '.format(self.host, time.strftime('%Y-%m-%d %H:%M:%S'))

    def download_war(self):
        return self.download_file(self.war_url, TOMCAT_DIR, fname=self.name+'.war')

    def do(self):
        real_war = os.path.join(self.war_dir, self.name)
        if os.path.exists(real_war):
            shutil.rmtree(real_war, ignore_errors=True)

        if os.path.exists(self.war_dir):
            war = self.download_war()
            self.log('移动War包到: %s' % self.war_dir)
            try:
                shutil.move(war, self.war_dir)
            except shutil.Error:
                self.log('该war包已经存在!')
                self.log('移除旧文件...')
                os.remove(os.path.join(self.war_dir, os.path.basename(war)))
                self.log('移动War包到: %s' % self.war_dir)
                shutil.move(war, self.war_dir)
            self.log('>>>>>>>>>>>>>>>>完成<<<<<<<<<<<<<<<<<<')
        else:
            self.log('指定的War包目录不存在 %s' % self.war_dir)


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
            task_info['priority'], task_info['jar'], task_info['conf'], task_info['pkg_dest_dir']
        )
    if type_ == 'tomcat':
        return TaskTomcatWar(
            task_info['host'], task_info['app_name'], task_info['identifier'],
            task_info['priority'], task_info['war_url'], task_info['war_dir']
        )
    if type_ == 'script':
        return TaskCustomScript(
            task_info['name'], task_info['identifier'], task_info['priority'],
            task_info['script_url']
        )


class Node(object):
    def __init__(self, ip):
        self._service = None
        self._ip = ip
        self._tasks = TaskQueue()
        self.cpu_monitor = MonitorCpu(self.id)
        self.memory_monitor = MonitorMemory(self.id)
        self.disk_monitor = MonitorDisk(self.id)

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

    def set_alarm_interval(self, interval):
        logger.info('Set alarm interval: %s' % interval)
        self.node.cpu_monitor.set_alarm_interval(interval)
        self.node.memory_monitor.set_alarm_interval(interval)
        self.node.disk_monitor.set_alarm_interval(interval)

    def start_monitor(self):
        logger.info('Start monitor...')
        self.node.cpu_monitor.start()
        self.node.memory_monitor.start()
        self.node.disk_monitor.start()

    def stop_monitor(self):
        logger.info('Stop monitor...')
        self.node.cpu_monitor.stop()
        self.node.memory_monitor.stop()
        self.node.disk_monitor.stop()

    def add_task(self, task_info):
        logger.info('Add task: %s' % task_info)
        task = task_factory(task_info)
        if task:
            self.node.add_task(task)
            logger.info('Added task: %s' % task.name)

    @staticmethod
    def path_exists(path):
        return os.path.exists(path)

    @staticmethod
    def create_path(path):
        try:
            os.makedirs(path)
            return True
        except OSError:
            # Permission denied
            return False

    @staticmethod
    def kill_process(cmd):
        logger.info('Received task: kill process - %s' % cmd)
        cmd_flag = os.path.sep.join(cmd.split(os.path.sep)[:3])
        for p in psutil.process_iter():
            if cmd_flag in ''.join(p.cmdline()):
                try:
                    p.kill()
                except psutil.AccessDenied:
                    logger.info('Kill process - %s FAILS -- AccessDenied' % cmd)
                    return False
                logger.info('Kill process - %s SUCCESS' % cmd)
                return True
        logger.info('Kill process - %s FAILS' % cmd)
        return False

    @staticmethod
    def tomcat_is_alive(cmd):
        cmd_flag = os.path.sep.join(cmd.split(os.path.sep)[:3])
        for p in psutil.process_iter():
            if cmd_flag in ''.join(p.cmdline()):
                return True
        return False

    @staticmethod
    def start_tomcat(cmd):
        logger.info('Received task: start tomcat - %s' % cmd)
        ret = os.system(cmd)
        if ret == 0:
            logger.info('Start tomcat - %s SUCCESS' % cmd)
            return True
        else:
            logger.info('Start tomcat - %s FAILS' % cmd)
            return False

    @staticmethod
    def get_base_info():
        return base_info()

    @staticmethod
    def get_netcard_info():
        return netcard_info()

    @staticmethod
    def get_runtime_info():
        return {
            'hostname': socket.gethostname(),
            'users': users(),
            'cpu': cpu(),
            'memory': memory(),
            'swap': swap_memory(),
            'disks': disks(),
            'uptime': datetime.datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S'),
        }

    @staticmethod
    def get_processes_info():
        return process_list()


class MarmotAgent(object):
    BIND_HOST = '0.0.0.0'
    PORT = 9001
    SYNC_INTERVAL = 2

    @classmethod
    def create_from_cli(cls):
        config = cls.handle_commandline()
        try:
            RDS.keys()
        except redis.RedisError:
            logger.error('Redis: ConnectionError')
            raise
        local_ip = get_local_ip(ifname=IFNAME)
        if local_ip is None:
            raise IOError('Get local ip error')
        try:
            conf = http_get_json(CONF_URL, {'ip': local_ip})
        except Exception:
            logger.error('Get node config error - %s' % CONF_URL)
            conf = DEFAULT_CONF
        conf['ip'] = local_ip
        config.update(conf)
        return cls(config)

    @staticmethod
    def handle_commandline():
        parser = argparse.ArgumentParser(description='Marmot -- agent')
        parser.add_argument('-b', '--bind',
                            action='store', dest='host', default=None, metavar='host',
                            help='host to bind default to 0.0.0.0')
        parser.add_argument('-p', '--port',
                            action='store', type=int, dest='port', default=None, metavar='port',
                            help='port to listen default to 9001')
        parser.add_argument('-d', '--debug',
                            action='store_true', dest='debug', default=False,
                            help='start agent debug mode')
        return vars(parser.parse_args())

    def __init__(self, config):
        self.config = config
        self.alarm_url = self.config.pop('alarm_url')
        self.monitor_conf = self.config.pop('monitor')
        self._service = Node(self.config.pop('ip')).get_service()
        if self.monitor_conf:
            self._service.set_memory_monitor_level(self.monitor_conf['memory'])
            self._service.set_disk_monitor_level(self.monitor_conf['disk'])
            self._service.set_alarm_interval(self.monitor_conf['alarm_interval'])
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

            gevent.sleep(interval)

    def _sync_worker(self, interval):
        logger.info('Starting sync-worker...')
        node_id = self._service.node.id
        while True:
            logger.debug('Sync node info to redis...')
            try:
                RDS.setex(node_id, 10, json.dumps(self._service.get_runtime_info()))
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
        self.server.logRequests = self.config['debug']
        self.server.register_instance(self._service)
        return self.server.serve_forever()

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

    file_handler = logging.FileHandler(LOG_File, mode='w')
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
