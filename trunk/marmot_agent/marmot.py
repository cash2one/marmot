#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division

import gevent
from gevent import monkey; monkey.patch_all()
from gevent.queue import PriorityQueue, Queue, Empty
from gevent import subprocess

import os
import platform
import time
import datetime
import socket
import fcntl
import struct
import re
import json
import shutil
import urllib
import urllib2
import zipfile
import hashlib
import tempfile
import stat
import signal
import logging
import argparse
import commands
from array import array
from SocketServer import ThreadingMixIn
from SimpleXMLRPCServer import SimpleXMLRPCServer

import psutil
import netifaces


__version__ = '2.15.0'


# **********************************************************************************
# 配置
# **********************************************************************************

MARMOT_HOST = '192.168.162.91'
MARMOT_PORT = 8100

ALLOW_CLIENT_HOSTS = (
    MARMOT_HOST, 'localhost', '127.0.0.1',
    '10.20.0.202', '172.16.20.48', '192.168.23.115'
)

SERVER_HOST = 'http://%s:%s' % (MARMOT_HOST, MARMOT_PORT)
REDIS_LOG_URL = '%s/redis-log/' % SERVER_HOST
LOG_BACKUP_API = '%s/springcloud/backup/create/' % SERVER_HOST  # 向web报告springcloud-app的备份地址
CONF_URL = '%s/assets/server/conf/' % SERVER_HOST
PROCESS_MONITOR_URL = '%s/assets/server/process-monitors/' % SERVER_HOST
ALARM_URL = '%s/alarm/' % SERVER_HOST

DEFAULT_CONF = {
    'monitor': {
        'enabled': False,
        'cpu': 99.0,
        'memory': 90,
        'disk': 90,
        'alarm_interval': 20,
    }
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
if not os.path.isdir(SCRIPTS_DIR):
    os.mkdir(SCRIPTS_DIR)

ICE_PROJECT_DIR = '/tmp'
TOMCAT_DIR = '/tmp'
STORM_DIR = '/tmp'

LOG_File = 'MarmotAgent.log'
logger = logging.Logger('MarmotAgent')


# **********************************************************************************
# 获取机器的静态信息
# **********************************************************************************


def dmidecode_system(pattern=re.compile(r'System Information\n\tManufacturer: (?P<manufacturer>.*)\n'
                                        r'\tProduct Name: (?P<product_name>.*)\n'
                                        r'\tVersion: (?P<version>.*)\n'
                                        r'\tSerial Number: (?P<serial_number>.*)\n'
                                        r'\tUUID: (?P<uuid>.*)\n'
                                        r'\t(.)*\n'
                                        r'\t(.)*\n'
                                        r'\tFamily: (?P<family>.*)\n')):

    content = subprocess.check_output(['sudo', 'dmidecode'])
    match = re.search(pattern, content)
    return {
        'manufacturer': match.group('manufacturer'),
        'product-name': match.group('product_name'),
        'version': match.group('version'),
        'serial-number': match.group('serial_number'),
        'uuid': match.group('uuid'),
        'family:': match.group('family'),
    }


def _linux_os_release():
    """Try to determine the name of a Linux distribution.
    This function checks for the /etc/os-release file.
    It takes the name from the 'NAME' field and the version from 'VERSION_ID'.
    An empty string is returned if the above values cannot be determined.
    """
    pretty_name = ''
    ashtray = {}
    keys = ['NAME', 'VERSION_ID']
    try:
        with open(os.path.join('/etc', 'os-release')) as f:
            for line in f:
                for key in keys:
                    if line.startswith(key):
                        ashtray[key] = line.strip().split('=')[1][1:-1]
    except (OSError, IOError):
        return pretty_name

    if ashtray:
        if 'NAME' in ashtray:
            pretty_name = ashtray['NAME']
        if 'VERSION_ID' in ashtray:
            pretty_name += ' {}'.format(ashtray['VERSION_ID'])

    return pretty_name


def cpu_info(vendor_pattern=re.compile(r'vendor_id([ \t])+: (?P<vendor_id>.*)\n'),
             model_pattern=re.compile(r'model name([ \t])+: (?P<model_name>.*)\n'),
             processor_pattern=re.compile(r'(processor[ \t]+: \d+\n)')):

    with open('/proc/cpuinfo') as f:
        content = f.read()
        try:
            num = os.sysconf("SC_NPROCESSORS_ONLN")
        except ValueError:
            # as a second fallback we try to parse /proc/cpuinfo
            num = len(re.findall(processor_pattern, content))
        return {
            'vendor': re.search(vendor_pattern, content).group('vendor_id').strip(),
            'model': re.search(model_pattern, content).group('model_name').strip(),
            'core_num': num,
        }


def netcard_info():

    def _get_hwaddr(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
        return ':'.join(['%02x' % ord(char) for char in info[18:24]])

    ifaces = netifaces.interfaces()
    if 'lo' in ifaces:
        ifaces.remove('lo')
    ret = {}
    for i in ifaces:
        try:
            netcard = netifaces.ifaddresses(i)[netifaces.AF_INET][0]
        except KeyError:
            continue

        ret[i] = {
            'mac': _get_hwaddr(i),
            'broadcast': netcard['broadcast'],
            'mask': netcard['netmask'],
            'addr': netcard['addr'],
        }
    return ret


def socket_constants(prefix):
    return dict((getattr(socket, n), n) for n in dir(socket) if n.startswith(prefix))


SOCKET_FAMILIES = socket_constants('AF_')
SOCKET_TYPES = socket_constants('SOCK_')


# **********************************************************************************
# runtime info
# **********************************************************************************


def human_size(_bytes, traditional=((1024 ** 5, 'P'),
                                    (1024 ** 4, 'T'),
                                    (1024 ** 3, 'G'),
                                    (1024 ** 2, 'M'),
                                    (1024 ** 1, 'K'),
                                    (1024 ** 0, 'B'))):
    """Human-readable size"""
    for factor, suffix in traditional:
        if _bytes >= factor:
            amount = round(_bytes/factor, 2)
            return str(amount) + suffix
    else:
        return str(_bytes)


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
        'shared': '%.2fG' % (data.shared/divisor) if hasattr(data, 'shared') else '0',
        'active': '%.2fG' % (data.active/divisor),
        'inactive': '%.2fG' % (data.inactive/divisor),
        'buffers': '%.2fG' % (data.buffers/divisor),
        'cached': '%.2fG' % (data.cached/divisor),
    }


def swap_memory():
    sm = psutil.swap_memory()
    divisor = 1024**3
    return {
        'total': '%.2fG' % (sm.total/divisor),
        'free': '%.2fG' % (sm.free/divisor),
        'used': '%.2fG' % (sm.used/divisor),
        'percent': '{}%'.format(sm.percent),
        'swapped_in': '%.2fG' % (sm.sin/divisor),
        'swapped_out': '%.2fG' % (sm.sout/divisor),
    }


def cpu():
    cpu_times = psutil.cpu_times_percent(0)
    return {
        'user': cpu_times.user,
        'system': cpu_times.system,
        'idle': cpu_times.idle,
        'iowait': cpu_times.iowait,
        'loadavg': os.getloadavg(),
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


class NetIOCounters(object):
    def __init__(self, pernic=True):
        self.last_req = None
        self.last_req_time = None
        self.pernic = pernic

    def _get_net_io_counters(self):
        """
        Fetch io counters from psutil and transform it to
        dicts with the additional attributes defaulted
        """
        counters = psutil.net_io_counters(pernic=self.pernic)

        res = {}
        for name, io in counters.iteritems():
            res[name] = io._asdict()
            res[name].update({'tx_per_sec': 0, 'rx_per_sec': 0})

        return res

    def _set_last_request(self, counters):
        self.last_req = counters
        self.last_req_time = time.time()

    def get(self):
        return self.last_req

    def update(self):
        counters = self._get_net_io_counters()

        if not self.last_req:
            self._set_last_request(counters)
            return counters

        time_delta = time.time() - self.last_req_time
        if not time_delta:
            return counters

        for name, io in counters.iteritems():
            last_io = self.last_req.get(name)
            if not last_io:
                continue

            counters[name].update({
                'rx_per_sec': (io['bytes_recv'] - last_io['bytes_recv']) / time_delta,
                'tx_per_sec': (io['bytes_sent'] - last_io['bytes_sent']) / time_delta
            })

        self._set_last_request(counters)

        return counters


def get_interface_addresses():
    """
    Get addresses of available network interfaces.
    See netifaces on pypi for details.
    """
    addresses = []
    ifaces = netifaces.interfaces()
    for iface in ifaces:
        addrs = netifaces.ifaddresses(iface)
        families = addrs.keys()

        # put IPv4 to the end so it lists as the main iface address
        if netifaces.AF_INET in families:
            families.remove(netifaces.AF_INET)
            families.append(netifaces.AF_INET)

        for family in families:
            for addr in addrs[family]:
                address = {
                    'name': iface,
                    'family': family,
                    'ip': addr['addr'],
                }
                addresses.append(address)

    return addresses


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


class Timer(object):

    def __init__(self, interval):
        self._interval = interval  # second
        self._st = time.time()

    def set_interval(self, interval):
        self._interval = interval

    def reset(self):
        self._st = time.time()

    def done(self):
        return (time.time() - self._st) >= self._interval


class Buffer(object):

    def __init__(self, size, atype='f'):
        self._atype = atype
        self._size = size
        self._items = array(atype, [])

    def size(self):
        return len(self._items)

    def append(self, item):
        if len(self._items) >= self._size:
            del self._items[0]
        self._items.append(item)

    def pre_items(self, x):
        return self._items[0:x].tolist()

    def xmean(self, x):
        return sum(self._items[0:x]) / x

    def preview(self):
        return self._items.tolist()

    def flush(self):
        self._items = array(self._atype, [])

    def mean(self):
        return sum(self._items) / len(self._items)

    def sum(self):
        return sum(self._items)


class Alarm(object):
    """
    level: 1(一般), 2(中级), 3(严重)
    type: cpu, memory, disk, port, process
    """
    def __init__(self, host, type_, msg, level=1):
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


class Actor(gevent.Greenlet):

    def __init__(self, interval):
        super(Actor, self).__init__()
        self._inbox = Queue()
        self._interval = interval
        self._timeout = None

    def work(self):
        """
        Define in your subclass.
        """
        raise NotImplemented()

    def _run(self):
        while True:
            try:
                msg = self._inbox.get(block=True, timeout=self._timeout)
                if msg == 'stop':
                    self._timeout = None
                elif msg == 'start':
                    self._timeout = self._interval
                elif msg == 'shutdown':
                    break
            except Empty:
                try:
                    self.work()
                except Exception:
                    logger.exception('UnknowError')
            gevent.sleep(0)

    def start(self):
        self._inbox.put('start')
        return super(Actor, self).start()

    def stop(self):
        self._inbox.put('stop')

    def shutdown(self):
        self._inbox.put('shutdown')


class BaseMonitor(Actor):
    alarm_url = ALARM_URL

    def __init__(self, host, name=None, work_interval=5, alarm_interval=20):
        """
        work_interval: Second
        alarm_interval: Minutes
        """
        super(BaseMonitor, self).__init__(work_interval)
        self.host = host
        self.name = name or self.__class__.__name__
        self.alarm_countor = 0
        self.alarm_timer = Timer(60*alarm_interval)

    def reset_alarm_countor(self):
        self.alarm_countor = 0

    def increase_alarm_countor(self):
        self.alarm_countor += 1

    def set_alarm_interval(self, interval):
        """ interval: Minutes """
        self.alarm_timer.set_interval(60*interval)

    def _send_alarm(self, alarm):
        logger.info('%s: send alarm %s' % (self.name, alarm.message()))
        url = self.alarm_url + '?' + urllib.urlencode(alarm.message())
        req = urllib2.Request(url)
        res = urllib2.urlopen(req)
        return json.loads(res.read())

    def get_alarm(self):
        raise NotImplementedError

    def work(self):
        logger.debug('%s is running...' % self.name)
        alarm = self.get_alarm()
        if alarm:
            if self.alarm_countor:
                if self.alarm_timer.done():
                    self._send_alarm(alarm)
                    self.alarm_timer.reset()
            else:
                self._send_alarm(alarm)
                self.increase_alarm_countor()
                self.alarm_timer.reset()
        else:
            self.alarm_timer.reset()
            self.reset_alarm_countor()


class ProcessMonitor(BaseMonitor):
    process_monitor_url = PROCESS_MONITOR_URL

    def __init__(self, host, alarm_interval=20):
        super(ProcessMonitor, self).__init__(host, work_interval=10, alarm_interval=alarm_interval)

    @staticmethod
    def check_process(process):
        for p in psutil.process_iter():
            if process in ''.join(p.cmdline()):
                return True
        return False

    def _get_process_monitors(self):
        url = self.process_monitor_url + '?' + urllib.urlencode({'hostname': self.host})
        req = urllib2.Request(url)
        res = urllib2.urlopen(req)
        return json.loads(res.read())['monitors']

    def get_alarm(self):
        try:
            monitors = self._get_process_monitors()
        except IOError:
            return
        if not monitors:
            return
        listening_ports = listening_port_set()
        for monitor in monitors:
            if not self.check_process(monitor['cmd']):
                return Alarm(
                    self.host, 'process',
                    '{0} - {1}: {2} - 进程: {3}未存活'.format(self.host, self.name, monitor['name'], monitor['process']),
                    level=3
                )
            if monitor['port'] not in listening_ports:
                return Alarm(
                    self.host, 'port',
                    '{0} - {1}: {2} - 端口: {3}未被占用'.format(self.host, self.name, monitor['name'], monitor['port']),
                    level=3
                )


class CpuMonitor(BaseMonitor):
    """
    Cpu负载监视器
    """
    def __init__(self, host, alarm_interval=20):
        super(CpuMonitor, self).__init__(host, work_interval=2, alarm_interval=alarm_interval)
        # 监控Actor的interval是2second, 这里缓冲1小时的数据, 即1800个数据
        self._buf = Buffer(1800)

    def load_avg(self):
        # TODO CPU负载监控有待改进, 应该用loadavg去判断负载情况
        self._buf.append(psutil.cpu_percent())  # 刷新缓冲
        return {
            'avg10': self._buf.xmean(10 * 30),
            'avg30': self._buf.xmean(30 * 30),
            'avg60': self._buf.xmean(60 * 30),
        }

    def get_alarm(self):
        avg = self.load_avg()
        if avg['avg60'] >= 99.0:
            return Alarm(self.host, 'cpu', '{0} - {1}: Cpu负载已经持续1小时超过99%'.format(self.host, self.name), level=3)
        if avg['avg30'] >= 99.0:
            return Alarm(self.host, 'cpu', '{0} - {1}: Cpu负载已经持续30分钟超过99%'.format(self.host, self.name), level=2)
        if avg['avg10'] >= 99.0:
            return Alarm(self.host, 'cpu', '{0} - {1}: Cpu负载已经持续10分钟超过99%'.format(self.host, self.name), level=1)


class MemoryMonitor(BaseMonitor):
    """
    Memory监视器
    """
    def __init__(self, host, level=80, alarm_interval=20):
        super(MemoryMonitor, self).__init__(host, alarm_interval=alarm_interval)
        self._alarm_level = level
        self._buf = Buffer(6)

    def set_alarm_level(self, level):
        self._alarm_level = level

    def get_alarm(self):
        self._buf.append(psutil.virtual_memory().percent)
        used = self._buf.mean()
        if used >= self._alarm_level:
            return Alarm(self.host, 'memory', '{0} - {1}: 内存占用: {2}%'.format(self.host, self.name, used), level=2)


class DiskMonitor(MemoryMonitor):
    """
    Disk监视器
    """
    def get_alarm(self):
        for disk in disks():
            if disk['percent'] >= self._alarm_level:
                return Alarm(
                    self.host, 'disk',
                    '{0} - {1}: 挂载点: {2}, 使用: {3}%'.format(self.host, self.name,
                                                           disk['mountpoint'], disk['percent']),
                    level=2
                )


class PortMonitor(BaseMonitor):
    """
    Port监视器
    """
    def __init__(self, host, alarm_interval=20):
        super(PortMonitor, self).__init__(host, alarm_interval=alarm_interval)
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
                return Alarm(self.host, 'port', '{0}: 监听端口{1}没有被监听'.format(self.host, not_ports), level=2)

        if self.deny_ports:
            tmp = self.deny_ports & listening_ports
            if tmp:
                return Alarm(self.host, 'port', '{0}: 开放端口{1}被占用'.format(self.host, tmp), level=1)


# **********************************************************************************
# utils
# **********************************************************************************


def http_get_json(url, param=None):
    if param:
        url = url + '?' + urllib.urlencode(param)
    req = urllib2.Request(url)
    resp = urllib2.urlopen(req)
    return json.loads(resp.read())


def http_post_json(url, data):
    req = urllib2.Request(url, json.dumps(data))
    resp = urllib2.urlopen(req)
    return json.loads(resp.read())


def zip_dir(dirname, zfname=None):
    if zfname is None:
        zfname = os.path.basename(os.path.normpath(dirname)) + '.zip'
    zf = zipfile.ZipFile(zfname, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True)
    base_len = len(dirname)
    for root, dirs, files in os.walk(dirname):
        for d in dirs:
            fn = os.path.join(root, d)
            zf.write(fn, fn[base_len:])
        for f in files:
            fn = os.path.join(root, f)
            zf.write(fn, fn[base_len:])
    zf.close()
    return zfname


def unzip(filename, to_dir):
    zf = zipfile.ZipFile(filename, 'r')
    zf.extractall(to_dir)
    zf.close()


def get_first_dir_name(zfname):
    """
    获取zip文件中的第一级目录的名字
    """
    zf = zipfile.ZipFile(zfname)
    dirs = [i.split('/')[0] for i in zf.namelist() if '/' in i]
    zf.close()
    return list(set(dirs))


def backup_dir(dirname):
    dt = time.strftime('%Y%m%d%H%M%S')
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
            shutil.rmtree(filepath, ignore_errors=False)


def tail_file(filename, offset, length):

    def as_string(s):
        return s if isinstance(s, unicode) else s.decode('utf-8')

    try:
        with open(filename, 'rb') as f:
            overflow = False
            f.seek(0, 2)
            sz = f.tell()

            if sz > (offset + length):
                overflow = True
                offset = sz - 1

            if (offset + length) > sz:
                if offset > (sz - 1):
                    length = 0
                offset = sz - length

            if offset < 0:
                offset = 0
            if length < 0:
                length = 0

            if length == 0:
                data = ''
            else:
                f.seek(offset)
                data = f.read(length)

            offset = sz
            return [as_string(data), offset, overflow]
    except (OSError, IOError):
        return ['', offset, False]


# **********************************************************************************
# Task
# **********************************************************************************


class TaskQueue(PriorityQueue):
    def add_task(self, task, block=True, timeout=None):
        self.put((task.priority, task), block=block, timeout=timeout)

    def pop_task(self, block=True, timeout=None):
        return self.get(block=block, timeout=timeout)[1]


class TaskBase(object):
    redis_log_url = REDIS_LOG_URL

    def __init__(self, name, identifier, priority):
        logger.info('Construct Task: %s uuid: %s ...' % (name, identifier))
        self.name = name
        self.identifier = identifier
        self.priority = int(priority)
        self._log_init()

    def header(self):
        return '[%s] ' % time.strftime('%Y-%m-%d %H:%M:%S')

    def check_md5(self, fname, md5):
        """校验md5, 检查文件传输的完整性"""
        basename = os.path.basename(fname)
        self.log('MD5校验: %s ...' % basename)
        if hashlib.md5(open(fname, 'rb').read()).hexdigest() == md5:
            self.log('MD5校验 - OK, 文件: %s' % basename)
        else:
            raise ValueError('MD5校验 - FAILED, 文件下载失败: %s' % basename)

    def _log_init(self):
        return http_post_json(self.redis_log_url, {
                'act': 'init',
                'id': self.identifier,
            })

    def log(self, info):
        return http_post_json(self.redis_log_url, {
                'act': 'log',
                'id': self.identifier,
                'msg': self.header() + info
            })

    def do(self):
        raise NotImplementedError


class DownloadMixin(object):
    def callback_progress(self, blocknum, blocksize, totalsize):
        percent = 100.0 * blocknum * blocksize / totalsize
        if percent > 100:
            percent = 100
        self.log('%.2f%%' % percent)

    def download_file(self, url, to_dir, fname=None):
        basename = os.path.basename(url) if fname is None else fname
        filename = os.path.join(to_dir, basename)
        if not os.path.isdir(to_dir):
            os.makedirs(to_dir)
        logger.info('Starting to download file: %s ...' % url)
        self.log('开始下载文件: %s ...' % basename)
        try:
            urllib.urlretrieve(url, filename)
        except Exception as e:
            logger.exception('Download file FAILED: %s' % url)
            self.log('错误: ' + str(e))
            return
        logger.info('Success to download file: %s' % url)
        self.log('下载完成: %s' % basename)
        return filename


class TaskIceDeploy(DownloadMixin, TaskBase):
    def __init__(self, node_name, service_name, identifier, priority,
                 jar, jar_md5, conf, conf_md5, pkg_dest_path):
        super(TaskIceDeploy, self).__init__(service_name, identifier, priority)
        self.node_name = node_name.encode('utf-8')
        self.jar = jar
        self.jar_md5 = jar_md5
        self.conf = conf
        self.conf_md5 = conf_md5
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
        self.log('处理文件 ...')
        lib_path = os.path.join(self._pkg_dest_path, 'lib')
        os.mkdir(lib_path)
        shutil.move(jar, lib_path)
        if conf:
            unzip(conf, self._pkg_dest_path)
        self.log('文件处理完成...')
        self.log('>>>>>>>>>>>>>>>>完成<<<<<<<<<<<<<<<<<<')

    def do(self):
        jar = self.download_jar()
        conf = self.download_conf()
        if jar:
            self.check_md5(jar, self.jar_md5)
        if conf:
            self.check_md5(conf, self.conf_md5)
        if jar:
            self.deploy(jar, conf)
        else:
            self.log('jar包地址有误, 部署失败')


class TaskIceSyncXml(object):
    """
    这个Task只需要默默的将ice的xml配置文件同步到config目录下配用即可,
    不需要回显运行过程
    """
    def __init__(self, name=None, priority=None,
                 xml_url=None, to_dir=None, xml_md5=None):
        logger.info('Received TaskIceSyncXml: %s' % name)
        self.name = name
        self.priority = priority
        self.xml_url = xml_url
        self.to_dir = to_dir
        self.xml_md5 = xml_md5

    def download(self):
        basename = os.path.basename(self.xml_url)
        filename = os.path.join(self.to_dir, basename)
        logger.info('Starting to download xml: %s ...' % self.xml_url)
        try:
            urllib.urlretrieve(self.xml_url, filename)
        except Exception:
            logger.exception('Download xml FAILED: %s' % self.xml_url)
            return
        logger.info('Success to download xml: %s' % self.xml_url)
        return filename

    def check_md5(self, fname):
        basename = os.path.basename(fname)
        if hashlib.md5(open(fname, 'rb').read()).hexdigest() == self.xml_md5:
            logger.info('Check xml MD5 - OK, 文件: %s' % basename)
        else:
            os.remove(fname)
            logger.warning('Check xml MD5 - FAILED, 文件: %s' % basename)

    def do(self):
        try:
            filename = self.download()
            if filename:
                self.check_md5(filename)
            logger.info('TaskIceSyncXml: %s - OK' % self.name)
        except Exception:
            logger.exception('TaskIceSyncXml: %s - ERROR' % self.name)


class TaskStormJar(DownloadMixin, TaskBase):
    def __init__(self, host, app_name, identifier, priority, jar_url, jar_md5, jar_dir):
        super(TaskStormJar, self).__init__(app_name, identifier, priority)
        self.host = host
        self.jar_url = jar_url
        self.jar_md5 = jar_md5
        self.jar_dir = jar_dir

    def header(self):
        return '{0} :: {1} :: '.format(self.host, time.strftime('%Y-%m-%d %H:%M:%S'))

    def download_jar(self):
        return self.download_file(self.jar_url, STORM_DIR, fname=self.name+'.jar')

    def do(self):
        if not os.path.exists(self.jar_dir):
            raise ValueError('指定的Jar包目录不存在 %s' % self.jar_dir)

        jar = self.download_jar()
        if not os.path.isfile(jar):
            raise ValueError('文件不存在!' % str(os.path.basename(jar)))

        self.check_md5(jar, self.jar_md5)

        self.log('移动Jar包到: %s' % self.jar_dir)

        # 如果war包文件已经存在, 删除之
        if os.path.isfile(os.path.join(self.jar_dir, os.path.basename(jar))):
            self.log('该Jar包: %s 已经存在!' % str(os.path.join(self.jar_dir, os.path.basename(jar))))
            self.log('移除旧jar包...')
            try:
                os.remove(os.path.join(self.jar_dir, os.path.basename(jar)))
            except OSError:  # Permission denied
                self.log('ERROR: 不能移除jar包: %s Permission denied' % str(os.path.join(self.jar_dir, os.path.basename(jar))))
                raise
            self.log('旧Jar包已经移除')
            self.log('开始复制新Jar包')

        shutil.move(jar, self.jar_dir)

        self.log('>>>>>>>>>>>>>>>>完成<<<<<<<<<<<<<<<<<<')


class TaskRunStormJar(TaskBase):
    def __init__(self, host, app_name, identifier, priority, jar_url, jar_md5, jar_dir, jar_main_function, jar_args):
        super(TaskRunStormJar, self).__init__(app_name, identifier, priority)
        self.host = host
        self.jar_url = jar_url
        self.jar_md5 = jar_md5
        self.jar_dir = jar_dir
        self.jar_main_function = jar_main_function
        self.jar_args = jar_args

    def header(self):
        return '{0} :: {1} :: '.format(self.host, time.strftime('%Y-%m-%d %H:%M:%S'))

    def do(self):
        if not os.path.exists(self.jar_dir):
            self.log('指定的Jar包目录不存在 %s' % self.jar_dir)
            raise ValueError('指定的Jar包目录不存在 %s' % self.jar_dir)
        jar = '%s/%s.jar' % (self.jar_dir, self.name)
        if not os.path.isfile(jar):
            self.log('文件不存在, 请推送jar文件!' % str(os.path.basename(jar)))
            raise ValueError('文件不存在, 请推送jar文件!' % str(os.path.basename(jar)))

        self.check_md5(jar, self.jar_md5)

        cmd = 'storm jar %s %s %s' % (jar, self.jar_main_function, self.jar_args)
        self.log('运行storm任务 %s' % cmd)
        try:
            status, output = commands.getstatusoutput('sudo su - storm -c "%s"' % cmd)
            if status == 0:
                self.log('Run - [ %s ] SUCCESS' % cmd)
                self.log(output)
                return True
            else:
                self.log('Run - [ %s ] FAILED' % cmd)
                self.log(output)
                return False
        except Exception as e:
            self.log(str(e))
            return False
        finally:
            self.log('>>>>>>>>>>>>>>>>任务完成<<<<<<<<<<<<<<<<<<')


class TaskTomcatWar(DownloadMixin, TaskBase):
    def __init__(self, host, app_name, identifier, priority, war_url, war_md5, war_dir):
        super(TaskTomcatWar, self).__init__(app_name, identifier, priority)
        self.host = host
        self.war_url = war_url
        self.war_md5 = war_md5
        self.war_dir = war_dir

    def header(self):
        return '{0} :: {1} :: '.format(self.host, time.strftime('%Y-%m-%d %H:%M:%S'))

    def download_war(self):
        return self.download_file(self.war_url, TOMCAT_DIR, fname=self.name+'.war')

    def do(self):
        if not os.path.exists(self.war_dir):
            raise ValueError('指定的War包目录不存在 %s' % self.war_dir)

        war = self.download_war()
        if not os.path.isfile(war):
            raise ValueError('文件不存在!' % str(os.path.basename(war)))

        self.check_md5(war, self.war_md5)

        # 移除tomcat解压的war的目录
        real_war = os.path.join(self.war_dir, self.name)
        if os.path.exists(real_war):
            shutil.rmtree(real_war, ignore_errors=True)

        # 移除ROOT
        root_path = os.path.join(self.war_dir, 'ROOT')
        if os.path.exists(root_path):
            self.log('移除ROOT目录')
            shutil.rmtree(root_path, ignore_errors=True)

        self.log('移动War包到: %s' % self.war_dir)

        # 如果war包文件已经存在, 删除之
        if os.path.isfile(os.path.join(self.war_dir, os.path.basename(war))):
            self.log('该War包: %s 已经存在!' % str(os.path.join(self.war_dir, os.path.basename(war))))
            self.log('移除旧War包...')
            try:
                os.remove(os.path.join(self.war_dir, os.path.basename(war)))
            except OSError:  # Permission denied
                self.log('ERROR: 不能移除War包: %s Permission denied' % str(os.path.join(self.war_dir, os.path.basename(war))))
                raise
            self.log('旧War包已经移除')
            self.log('开始安装新War包')

        shutil.move(war, self.war_dir)

        self.log('>>>>>>>>>>>>>>>>完成<<<<<<<<<<<<<<<<<<')


class TaskTomcatStatic(DownloadMixin, TaskBase):
    def __init__(self, host, app_name, identifier, priority, html_url, html_md5, html_dir):
        super(TaskTomcatStatic, self).__init__(app_name, identifier, priority)
        self.host = host
        self.html_url = html_url
        self.html_md5 = html_md5
        self.html_dir = html_dir

    def header(self):
        return '{0} :: {1} :: '.format(self.host, time.strftime('%Y-%m-%d %H:%M:%S'))

    def download_html_pkg(self):
        return self.download_file(self.html_url, '/tmp')

    def do(self):
        if not os.path.exists(self.html_dir):
            raise ValueError('目录不存在 %s' % self.html_dir)

        if not os.access(self.html_dir, os.W_OK):
            raise ValueError('目录没有写权限 %s' % self.html_dir)

        # 验证下载的静态文件zip包
        html_tmp_pkg = self.download_html_pkg()
        if not os.path.isfile(html_tmp_pkg):
            raise ValueError('文件不存在 %s' % str(os.path.basename(html_tmp_pkg)))

        self.check_md5(html_tmp_pkg, self.html_md5)

        first_dir_name = get_first_dir_name(html_tmp_pkg)
        if len(first_dir_name) > 1:
            raise ValueError('静态文件zip包有问题, 第一层应该只有一个目录!')

        web_html_dir = os.path.join(self.html_dir, first_dir_name[0])
        if os.path.isdir(web_html_dir):
            self.log('目录已经存在 - %s' % str(web_html_dir))
            self.log('开始备份...')
            backup_dir(web_html_dir)
            self.log('备份完成!')
            clear_dir(web_html_dir)

        unzip(html_tmp_pkg, self.html_dir)
        self.log('>>>>>>>>>>>>>>>>完成<<<<<<<<<<<<<<<<<<')


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
            logger.error('Download script FAILED: %s' % self._script_url)
            self.log(str(e))
            return
        else:
            logger.info('Success to download script: %s' % self._script_url)
            self.log('脚本下载完成: %s' % self._script_url)
        self.log('运行脚本...')
        self.run_script()
        self.log('脚本运行成功')


class TaskDownloadFile(DownloadMixin, TaskBase):
    def __init__(self, name=None, identifier=None, priority=None,
                 file_url=None, to_dir=None, file_md5=None):
        super(TaskDownloadFile, self).__init__(name, identifier, priority)
        self.file_url = file_url
        self.to_dir = to_dir
        self.file_md5 = file_md5

    def do(self):
        filename = self.download_file(self.file_url, self.to_dir)
        self.check_md5(filename, self.file_md5)
        self.log('>>>>>>>>>>>>>>>>成功<<<<<<<<<<<<<<<<<<')


class TaskSyncSpringCloudFiles(DownloadMixin, TaskBase):
    def __init__(self, name=None, cwd=None, identifier=None,
                 priority=None, files=None, clear=False):
        super(TaskSyncSpringCloudFiles, self).__init__(name, identifier, priority)
        self.files = files
        self.cwd = cwd
        self.appname = name
        self.clear = clear
        self.log_backup_api = LOG_BACKUP_API

    def sync_startup_sh(self):
        """同步app的启动脚本"""
        task_sync_sh = self.files.pop(0)  # 默认第一个是同步启动脚本的任务
        bin_cwd = os.path.join(self.cwd, 'bin')
        if not os.path.isdir(bin_cwd):
            try:
                os.makedirs(bin_cwd)
            except OSError:
                raise OSError('%s 目录不存在, 并且无法创建' % str(bin_cwd))

        if not os.access(bin_cwd, os.W_OK):
            raise OSError('%s 没有写权限!' % str(bin_cwd))

        if task_sync_sh:
            self.log('同步启动脚本...')
            fn = task_sync_sh['rel_path']
            if os.path.isfile(fn):
                if task_sync_sh['md5'] == hashlib.md5(open(fn, 'rb').read()).hexdigest():
                    self.log('md5值相同, 不处理')
                    return
                else:
                    self.log('备份原启动脚本...')
                    bak_dir = os.path.join(bin_cwd, 'bak')
                    if not os.path.isdir(bak_dir):
                        os.makedirs(bak_dir)
                    dt = time.strftime('%Y%m%d%H%M%S')
                    bak_path = os.path.join(bak_dir, 'bak-{0}-{1}'.format(dt, os.path.basename(fn)))
                    shutil.move(fn, bak_path)
                    self.log('备份完成: {0}'.format(bak_path))

            new_fn = self.download_file(task_sync_sh['url'], bin_cwd)
            if new_fn:
                self.check_md5(new_fn, task_sync_sh['md5'])
            else:
                raise ValueError('下载文件错误!')

    def log_backup_path(self, appname, path):
        """向web端报告备份文件的路径"""
        return http_post_json(self.log_backup_api, {
                'appname': appname,
                'path': path,
                'hostname': platform.node(),
            })

    def process_project_dir(self):
        """验证app的工程目录, 如果目录已经存在, 就先备份"""
        cwd = os.path.join(self.cwd, 'app', self.appname)
        if os.path.exists(cwd):
            self.log('工程目录已经存在 - %s' % str(cwd))
            if not os.access(cwd, os.W_OK):
                raise ValueError('目录没有写权限 %s' % str(cwd))
            if os.listdir(cwd):
                # 目录不为空才备份
                self.log('开始备份...')
                bak_path = backup_dir(cwd)
                self.log_backup_path(self.appname, bak_path)
                self.log('备份完成!')
        else:
            try:
                os.makedirs(cwd)
                self.log('创建目录 %s' % str(cwd))
            except OSError:
                raise ValueError('%s 目录不存在, 并且无法创建' % str(cwd))

    def do(self):
        self.sync_startup_sh()
        gevent.sleep(0)
        self.process_project_dir()
        gevent.sleep(0)

        cwd = os.path.join(self.cwd, 'app', self.appname)
        self.log('开始同步...')

        now_all_files = []  # 现在工程目录中的所有文件
        for root, dirs, files in os.walk(cwd):
            for f in files:
                now_all_files.append(os.path.join(root, f))

        # 服务器传过来的文件
        for f in self.files:
            full_path = os.path.join(cwd, f['rel_path'])
            self.log('同步 {0}'.format(full_path))
            try:
                now_all_files.remove(full_path)
            except ValueError:
                pass
            else:
                self.log('文件存在! 校验md5...')
                now_md5 = hashlib.md5(open(full_path, 'rb').read()).hexdigest()
                if now_md5 == f['md5']:
                    self.log('md5值相同, 不处理')
                    continue
                else:
                    self.log('md5值不同: %s -- %s' % (now_md5, f['md5']))

            filename = self.download_file(f['url'], os.path.dirname(full_path))
            if filename:
                self.check_md5(filename, f['md5'])
                # 如果文件是zip文件, 解压到当前目录
                if full_path.endswith('.zip'):
                    self.log('解压zip文件: %s' % full_path)
                    unzip(full_path, os.path.dirname(full_path))
                    self.log('解压zip完成')
            else:
                raise ValueError('下载文件错误!')
            gevent.sleep(0)

        if self.clear:
            # 删除now_all_files中剩余的文件
            self.log('清除原工程目录中多余的文件...')
            for f in now_all_files:
                os.remove(f)
                self.log('Removed: %s' % f)
                gevent.sleep(0)

        self.log('>>>>>>>>>>>>>>>>成功<<<<<<<<<<<<<<<<<<')


class TaskSpringCloudRollBack(TaskBase):
    """回滚SpringCloudApp的工程文件"""
    def __init__(self, name=None, identifier=None, priority=None, path=None):
        super(TaskSpringCloudRollBack, self).__init__(name, identifier, priority)
        self.appname = name
        self.path = path  # 备份zip文件的路径
        self.log_backup_api = LOG_BACKUP_API
        self.cwd = os.path.join(os.path.dirname(os.path.dirname(path)), self.appname)

    def log_backup_path(self, appname, path):
        """向web端报告备份文件的路径"""
        return http_post_json(self.log_backup_api, {
                'appname': appname,
                'path': path,
                'hostname': platform.node(),
            })

    def process_project_dir(self):
        """验证app的工程目录, 如果目录已经存在, 就先备份"""
        if os.path.exists(self.cwd):
            self.log('工程目录已经存在 - %s' % str(self.cwd))
            if not os.access(self.cwd, os.W_OK):
                raise ValueError('目录没有写权限 %s' % str(self.cwd))
            if os.listdir(self.cwd):
                # 目录不为空才备份
                self.log('开始备份原工程目录...')
                bak_path = backup_dir(self.cwd)
                self.log_backup_path(self.appname, bak_path)
                self.log('备份完成!')
                self.log('清理原目录...')
                clear_dir(self.cwd)
                self.log('清理完成')

    def rollback(self):
        self.log('开始还原: %s' % self.path)
        unzip(self.path, self.cwd)
        self.log('还原完成')

    def do(self):
        self.process_project_dir()
        gevent.sleep(0)
        self.rollback()
        self.log('>>>>>>>>>>>>>>>>成功<<<<<<<<<<<<<<<<<<')


class NodeAppDeploy(DownloadMixin, TaskBase):
    def __init__(self, name=None, identifier=None, priority=None,
                 file_url=None, to_dir=None, file_md5=None):
        super(NodeAppDeploy, self).__init__(name, identifier, priority)
        self.file_url = file_url
        self.to_dir = to_dir
        self.file_md5 = file_md5

    def do(self):
        filename = self.download_file(self.file_url, '/tmp')
        self.check_md5(filename, self.file_md5)

        if not os.path.exists(self.to_dir):
            raise ValueError('目录不存在 %s' % self.to_dir)

        if not os.access(self.to_dir, os.W_OK):
            raise ValueError('目录没有写权限 %s' % self.to_dir)

        if not os.path.isfile(filename):
            raise ValueError('文件不存在 %s' % str(os.path.basename(filename)))

        first_dir_name = get_first_dir_name(filename)
        if len(first_dir_name) > 1:
            raise ValueError('静态文件zip包有问题, 第一层应该只有一个目录!')
        if first_dir_name[0] != self.name:
            raise ValueError('zip文件的第一级目录的名称应该为应用的名字')

        node_app_dir = os.path.join(self.to_dir, first_dir_name[0])
        if os.path.isdir(node_app_dir):
            self.log('目录已经存在 - %s' % str(node_app_dir))
            self.log('开始备份...')
            backup_dir(node_app_dir)
            self.log('备份完成!')
            clear_dir(node_app_dir)

        self.log('解压zip包')
        unzip(filename, self.to_dir)
        self.log('>>>>>>>>>>>>>>>>完成<<<<<<<<<<<<<<<<<<')


def task_factory(task_info):
    type_ = task_info.pop('type')
    if type_ == 'ice':
        return TaskIceDeploy(
                task_info['node_name'], task_info['name'], task_info['identifier'],
                task_info['priority'], task_info['jar'], task_info['jar_md5'],
                task_info['conf'], task_info['conf_md5'], task_info['pkg_dest_dir']
            )
    if type_ == 'ice_sync_xml':
        return TaskIceSyncXml(**task_info)
    if type_ == 'tomcat_war':
        return TaskTomcatWar(
                task_info['host'], task_info['app_name'], task_info['identifier'],
                task_info['priority'], task_info['war_url'], task_info['war_md5'],
                task_info['war_dir']
            )
    if type_ == 'tomcat_static':
        return TaskTomcatStatic(
                task_info['host'], task_info['app_name'], task_info['identifier'],
                task_info['priority'], task_info['html_url'], task_info['html_md5'],
                task_info['html_dir']
            )
    if type_ == 'sync_spring_cloud':
        return TaskSyncSpringCloudFiles(**task_info)
    if type_ == 'rollback_spring_cloud':
        return TaskSpringCloudRollBack(**task_info)
    if type_ == 'download_file':
        return TaskDownloadFile(**task_info)
    if type_ == 'node_app':
        return NodeAppDeploy(**task_info)
    if type_ == 'script':
        return TaskCustomScript(
                task_info['name'], task_info['identifier'],
                task_info['priority'], task_info['script_url']
            )
    if type_ == 'storm_jar':
        return TaskStormJar(
                task_info['host'], task_info['app_name'], task_info['identifier'],
                task_info['priority'], task_info['jar_url'], task_info['jar_md5'],
                task_info['jar_dir'],
            )
    if type_ == 'run_storm_jar':
        return TaskRunStormJar(
                task_info['host'], task_info['app_name'], task_info['identifier'],
                task_info['priority'], task_info['jar_url'], task_info['jar_md5'],
                task_info['jar_dir'],task_info['jar_main_function'],task_info['jar_args'],
            )


# **********************************************************************************
# Marmot RPC
# **********************************************************************************


class ThreadXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass


class XmlRpcServer(ThreadXMLRPCServer):

    def __init__(self, host, port):
        SimpleXMLRPCServer.__init__(self, (host, port), allow_none=True)
        self.allow_client_hosts = ALLOW_CLIENT_HOSTS

    def verify_request(self, request, client_address):
        """Verify request IP"""
        return client_address[0] in self.allow_client_hosts


class Node(object):
    def __init__(self):
        self.hostname = platform.node()
        self.net_io_counters = NetIOCounters()
        self._service = None
        self._tasks = TaskQueue()
        self.cpu_monitor = CpuMonitor(self.hostname)
        self.memory_monitor = MemoryMonitor(self.hostname)
        self.disk_monitor = DiskMonitor(self.hostname)
        # TODO ProcessMonitor有缺陷, 无法根据进程名准确确认进程
        # self.process_monitor = ProcessMonitor(self.hostname)

    @property
    def id(self):
        return self.hostname

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

    def is_alive(self):
        return '*'

    def get_version(self):
        return __version__

    def get_psutil_version(self):
        return psutil.__version__

    def get_system(self):
        _system = {
            'hostname': self.node.hostname,
            'os_name': platform.system(),
            'os_verbose': platform.platform(),
            'platform': platform.architecture()[0],
            'os_version': platform.release(),
        }
        linux_distro = platform.linux_distribution()
        if linux_distro[0] == '':
            _system['linux_distro'] = _linux_os_release()
        else:
            _system['linux_distro'] = ' '.join(linux_distro[:2])
        return _system

    def get_now(self):
        return time.strftime('%Y-%m-%d %H:%M:%S')

    def get_boot_time(self):
        uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())
        return str(uptime).split('.')[0]

    def get_loadavg(self):
        return os.getloadavg()

    def get_base_info(self):
        return {
            'hostname': self.node.hostname,
            'dmi': dmidecode_system(),
            'os_distribution': '-'.join(platform.linux_distribution()),
            'os_verbose': platform.platform(),
            'cpu_info': cpu_info(),
            'disk_size': '%sG' % disk_total()['total'],
            'memory_total': memory()['total'],
        }

    def get_netcard_info(self):
        return netcard_info()

    def get_runtime_data(self):
        return {
            'hostname': self.node.hostname,
            'platform': platform.platform(),
            'users': users(),
            'cpu': cpu(),
            'memory': memory(),
            'swap': swap_memory(),
            'disks': disks(),
            'uptime': self.get_boot_time(),
        }

    def get_process_list(self):
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
                'created': datetime.datetime.fromtimestamp(p.create_time()).strftime('%Y-%m-%d %H:%M:%S'),
                'mem_rss': human_size(mem.rss),
                'mem_vms': human_size(mem.vms),
                'mem_percent': '%.2f' % p.memory_percent() + '%',
                'cpu_percent': '%.2f' % p.cpu_percent(0) + '%',
            }
            p_list.append(proc)
        # 按cpu_percent排序
        p_list.sort(key=lambda x: x.get('cpu_percent'), reverse=True)
        return p_list

    def get_connections(self, family, type, state):
        # xmlrpclib 目前不支持关键字参数
        filters = {}
        if family:
            filters['family'] = family
        if type:
            filters['type'] = type
        if state:
            filters['state'] = state

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

    def get_network_interfaces(self):
        logger.debug('get_network_interfaces')

        io_counters = self.node.net_io_counters.get()
        addresses = get_interface_addresses()

        netifs = {}
        for addr in addresses:
            c = io_counters.get(addr['name'])
            if not c:
                continue
            netifs[addr['name']] = {
                'name': addr['name'],
                'ip': addr['ip'],
                'sent': human_size(c['bytes_sent']),
                'recv': human_size(c['bytes_recv']),
                'packets_sent': c['packets_sent'],
                'packets_recv': c['packets_recv'],
                'errors_in': str(c['errin']),
                'errors_out': str(c['errout']),
                'dropped_in': str(c['dropin']),
                'dropped_out': str(c['dropout']),
                'send_rate': human_size(round(c['tx_per_sec'], 2)),
                'recv_rate': human_size(round(c['rx_per_sec'], 2)),
            }
        # 目前xmlrpclib中long类型的数字不能序列化
        # 'exceptions.OverflowError'>:int exceeds XML-RPC limits"
        return netifs

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
        # self.node.process_monitor.set_alarm_interval(interval)

    def start_monitor(self):
        logger.info('Start monitors...')
        self.node.cpu_monitor.start()
        self.node.memory_monitor.start()
        self.node.disk_monitor.start()
        # self.node.process_monitor.start()

    def stop_monitor(self):
        logger.info('Stop monitors...')
        self.node.cpu_monitor.stop()
        self.node.memory_monitor.stop()
        self.node.disk_monitor.stop()
        # self.node.process_monitor.stop()

    def add_task(self, task_info):
        logger.info('Received task: %s' % task_info)
        try:
            task = task_factory(task_info)
        except Exception:
            logger.exception('add task error: %s' % task_info['identifier'])
            return False
        if task:
            self.node.add_task(task)
            logger.info('Added task: %s' % task.name)
            return True

    def download_file(self, url, dst_dir, identifier, fmd5):
        if not os.path.isdir(dst_dir):
            try:
                os.makedirs(dst_dir)
            except OSError:
                return False
        task_info = {
            'type': 'download_file',
            'name': 'DownLoadFile',
            'identifier': identifier,
            'priority': 1,
            'file_url': url,
            'to_dir': dst_dir,
            'file_md5': fmd5,
        }
        return self.add_task(task_info)

    def task_node_src_pkg(self, appname, url, dst_dir, identifier, fmd5):
        if not os.path.isdir(dst_dir):
            try:
                os.makedirs(dst_dir)
            except OSError:
                return False
        task_info = {
            'type': 'node_app',
            'name': appname,
            'identifier': identifier,
            'priority': 1,
            'file_url': url,
            'to_dir': dst_dir,
            'file_md5': fmd5,
        }
        return self.add_task(task_info)

    def springcloud_sync_files(self, appname, cwd, files, identifier, clear):
        if not os.path.isdir(cwd):
            return False, '目录不存在: %s' % str(cwd)

        if not os.access(cwd, os.W_OK):
            return False, '目录没有写权限: %s' % str(cwd)

        task_info = {
            'type': 'sync_spring_cloud',
            'name': appname,
            'identifier': identifier,
            'priority': 1,
            'files': files,
            'cwd': cwd,
            'clear': clear
        }
        return self.add_task(task_info), ''

    def springcloud_rollback(self, appname, identifier, path):
        task_info = {
            'type': 'rollback_spring_cloud',
            'name': appname,
            'identifier': identifier,
            'priority': 1,
            'path': path,
        }
        return self.add_task(task_info)

    def springcloud_start(self, startup):
        try:
            proc = subprocess.Popen(
                    [startup + ' start'], cwd=os.path.dirname(startup),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
                )
            stdout, _ = proc.communicate(timeout=50.0)
        except Exception as e:
            return str(e)
        return stdout

    def springcloud_stop(self, startup):
        try:
            proc = subprocess.Popen(
                    [startup + ' stop'], cwd=os.path.dirname(startup),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
                )
            stdout, _ = proc.communicate(timeout=50.0)
        except Exception as e:
            return str(e)
        return stdout

    def tail(self, filename):
        # TODO 用来模拟tail读取log日志
        return ''

    def path_exists(self, path):
        return os.path.exists(path)

    def makedirs(self, path):
        logger.info('makedirs: %s ...' % path)
        try:
            os.makedirs(path)
            return True
        except Exception:  # Permission denied
            return False

    def remove(self, path):
        try:
            if os.path.isfile(path):
                os.remove(path)
            return True, ''
        except Exception as e:
            return False, str(e)

    def pid_is_alive(self, pid):
        pids = [str(p.pid) for p in psutil.process_iter()]
        return str(pid) in pids

    def storm_is_alive(self, type):
        logger.info('Received task: storm_is_alive - %s' % type)
        result = False
        cmd_flag = ''
        if type == 'nimbus':
            cmd_flag = 'backtype.storm.daemon.nimbus'
        elif type == 'supervisor':
            cmd_flag = 'backtype.storm.daemon.supervisor'
        elif type == 'ui':
            cmd_flag = 'backtype.storm.ui.core'
        else:
            return result
        for p in psutil.process_iter():
            cmdline = ''.join(p.cmdline())
            if cmd_flag in cmdline and 'storm' in cmdline:
                result = True
        logger.info('return task: storm_is_alive - %s' % result)
        return result

    def start_storm(self, type):
        logger.info('Received task: start storm - %s' % type)
        result = False
        ret = 1
        cmd = ''
        if type == 'nimbus':
            cmd = 'storm nimbus &'
        elif type == 'supervisor':
            cmd = 'storm supervisor &'
        elif type == 'ui':
            cmd = 'storm ui &'
        else:
            return False
        try:
            ret = os.system('sudo su - storm -c "%s"' % cmd)
            if ret == 0:
                logger.info('Start storm - %s SUCCESS' % cmd)
                return True
            else:
                logger.info('Start   - %s FAILED' % cmd)
                return False
        except Exception,e:
            logger.info("%s:%s" %(Exception,e))
            return False
        
    def kill_storm(self, type):
        logger.info('Received task: kill storm - %s' % type)
        cmd_flag = ''
        if type == 'nimbus':
            cmd_flag = 'backtype.storm.daemon.nimbus'
        elif type == 'supervisor':
            cmd_flag = 'backtype.storm.daemon.supervisor'
        elif type == 'ui':
            cmd_flag = 'backtype.storm.ui.core'
        else:
            return False
        for p in psutil.process_iter():
            cmdline = ''.join(p.cmdline())
            if cmd_flag in cmdline and 'storm' in cmdline:
                try:
                    p.kill()
                    return True
                except psutil.AccessDenied:
                    ret = os.system('sudo su - storm -c "kill -9 %s"' % p.pid)
                    if ret == 0:
                        logger.info('Kill strom - %s SUCCESS' % type)
                        return True
                    else:
                        logger.info('Kill storm - %s FAILED -- AccessDenied' % type)
                        return False
        logger.info('Kill tomcat - %s FAILED. The process is not exists!' % type)
        return False

    def kill_pid(self, pid):
        logger.info('Kill Pid: %s ...' % pid)
        for p in psutil.process_iter():
            if str(pid) == str(p.pid):
                try:
                    p.kill()
                    return True
                except psutil.AccessDenied:
                    return False
        return False

    def startup_node_app(self, app_name, main_script, cwd):
        logger.info('Start NodeApp: %s ...' % app_name)
        logpath = tempfile.mktemp(suffix='.log', prefix=app_name)
        try:
            proc = subprocess.Popen(['node', main_script], cwd=os.path.join(cwd, app_name),
                                    stdout=open(logpath, 'w'), stderr=subprocess.STDOUT)
        except OSError as e:
            return -1, str(e)

        gevent.sleep(0.2)

        if proc.poll() is not None:
            # 如果进程还在运行,  poll()返回None
            # 如果进程已经结束返回retcode
            with open(logpath, 'r') as f:
                return -1, f.read()

        with open(logpath, 'r') as f:
            st = time.time()
            out = []
            while True:
                line = f.readline()
                if line:
                    out.append(line)
                else:
                    if time.time() - st > 1:
                        break
                    gevent.sleep(0.2)

        return proc.pid, '\n'.join(out)

    def tomcat_is_alive(self, cmd):
        cmd_flag = os.path.sep.join(cmd.split(os.path.sep)[:3]) + '/'
        for p in psutil.process_iter():
            cmdline = ''.join(p.cmdline())
            if cmd_flag in cmdline and 'java' in cmdline:
                return True
        return False

    def start_tomcat(self, cmd):
        logger.info('Received task: start tomcat - %s' % cmd)
        # ret = os.system('sudo su - www -c "%s"' % cmd)
        ret = os.system(cmd)
        if ret == 0:
            logger.info('Start tomcat - %s SUCCESS' % cmd)
            return True
        else:
            logger.info('Start tomcat - %s FAILED' % cmd)
            return False

    def kill_tomcat(self, cmd):
        logger.info('Received task: kill tomcat - %s' % cmd)
        cmd_flag = os.path.sep.join(cmd.split(os.path.sep)[:3]) + '/'
        for p in psutil.process_iter():
            cmdline = ''.join(p.cmdline())
            if cmd_flag in cmdline and 'java' in cmdline:
                try:
                    p.kill()
                    return True
                except psutil.AccessDenied:
                    ret = os.system('sudo su - www -c "kill -9 %s"' % p.pid)
                    if ret == 0:
                        logger.info('Kill tomcat - %s SUCCESS' % cmd)
                        return True
                    else:
                        logger.info('Kill tomcat - %s FAILED -- AccessDenied' % cmd)
                        return False
        logger.info('Kill tomcat - %s FAILED. The process is not exists!' % cmd)
        return False

    def netstat(self, port):
        try:
            return subprocess.check_output('netstat -an | grep %s' % port, shell=True)
        except subprocess.CalledProcessError:
            logger.exception('netstat ERROR')
            return ''

    def get_es_info(self, url):
        try:
            req = urllib2.Request(url)
            resp = urllib2.urlopen(req)
            return resp.read()
        except Exception:
            logger.exception('Get ES info ERROR')
            return ''

    def hbase_status_simple(self):
        try:
            proc = subprocess.Popen(
                    ['hbase', 'shell'], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                )
            out, _ = proc.communicate("status 'simple'\n")
            return out
        except Exception as e:
            return 'Error: ' + str(e)


class MarmotAgent(object):
    BIND_HOST = '0.0.0.0'
    PORT = 9001

    @classmethod
    def create_from_cli(cls):
        config = cls.handle_commandline()
        hostname = socket.gethostname()
        try:
            conf = http_get_json(CONF_URL, {'hostname': hostname})
        except IOError:
            logger.warning('Can not get node config - %s' % CONF_URL + hostname)
            conf = DEFAULT_CONF
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
        self.monitor_conf = self.config.pop('monitor')
        self._service = Node().get_service()
        if self.monitor_conf:
            self._service.set_memory_monitor_level(self.monitor_conf['memory'])
            self._service.set_disk_monitor_level(self.monitor_conf['disk'])
            self._service.set_alarm_interval(self.monitor_conf['alarm_interval'])
            if self.monitor_conf['enabled']:
                self._service.start_monitor()

    def _task_worker(self):
        logger.info('Starting task-worker...')
        task_queue = self._service.node.get_task_queue()
        while True:
            task = task_queue.pop_task()
            logger.info('Start run task: %s' % task.name)
            try:
                task.do()
            except Exception as e:
                logger.exception('TaskError - %s' % task.name)
                task.log("ERROR - " + str(e))

    def _net_io_counters_worker(self):
        logger.info('Starting net-io-counters-worker...')
        while True:
            logger.debug("Updating net io counters...")
            self._service.node.net_io_counters.update()
            gevent.sleep(3)

    def _setup_workers(self):
        gevent.spawn_later(1, self._task_worker)
        gevent.spawn_later(2, self._net_io_counters_worker)

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
        fmt='[%(asctime)s] %(levelname)s : %(message)s',
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
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info('Goodbye!!!')


if __name__ == '__main__':
    gevent.signal(signal.SIGQUIT, gevent.kill)
    main()
