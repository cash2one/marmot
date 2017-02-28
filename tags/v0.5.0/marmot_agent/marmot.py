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
import cStringIO
import subprocess
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
from collections import OrderedDict
from SimpleXMLRPCServer import SimpleXMLRPCServer

import redis
import psutil
import netifaces


# **********************************************************************************
# 用fdisk dmidecode ifconfig获取机器的静态信息
# **********************************************************************************

FDISK_LIST_CMD = ['sudo', 'fdisk', '-l']
DMIDECODE_CMD = ['sudo', 'dmidecode']
IFCONFIG_CMD = ['sudo', 'ifconfig']


def run_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = p.communicate()[0]
    return output


def machine_info():
    output = run_cmd(['sudo', 'dmidecode'])
    s = cStringIO.StringIO(output)
    for line in s:
        if 'System Information' not in line:
            continue
        else:
            break
    ret = {}
    for k in ('Manufacturer', 'ProductName', 'SerialNumber'):
        line = s.readline()
        ret[k] = line[line.find(':')+1:].strip()
    s.close()
    return ret


def cpu_info():
    _cpu_info = OrderedDict()
    _proc_info = OrderedDict()
    nprocs = 0
    with open('/proc/cpuinfo') as f:
        for line in f:
            if not line.strip():
                # end of one processor
                _cpu_info['proc%s' % nprocs] = _proc_info
                nprocs += 1
                _proc_info = OrderedDict()  # Reset
            else:
                if len(line.split(':')) == 2:
                    _proc_info[line.split(':')[0].strip()] = line.split(':')[1].strip()
                else:
                    _proc_info[line.split(':')[0].strip()] = ''
    proc = _cpu_info['proc0']
    return {
        'vendor': proc['vendor_id'],
        'model': proc['model name']
    }


def disk_size():
    output = run_cmd(['sudo', 'fdisk', '-l'])
    s = cStringIO.StringIO(output)
    size = 0
    for line in s:
        if 'Disk /dev' in line:
            line = line.strip()
            line = line[line.find(':') + 1:].strip()
            size += (float(line[:line.find(' ')]))
    return int(round(size))


def netcard_info():
    """只对CentOS, RedHat有用"""
    dd = {
        'card': {},
        'bond': {},
    }
    # 在CentOS系统中, 运行ifconfig, 物理网卡信息中包含此字符串, 虚拟网卡中不含此字符串
    cards = ['Interrupt']

    bond_path = '/proc/net/bonding'
    if os.path.exists(bond_path):
        for file in os.listdir(bond_path):
            cards.append(file)
            file_path = os.path.join(bond_path, file)
            returncode, res = run_cmd(['cat', file_path])
            dd['bond'][file] = []
            s = cStringIO.StringIO(res)
            for line in s:
                if 'Interface' in line:
                    dd['bond'][file].append(line[line.rfind(' '):].strip())
            s.close()

    res = run_cmd(['sudo', 'ifconfig']).split('\n\n')

    def get_field(netcard_info):
        ret = {}
        index = netcard_info.find('HWaddr')
        if index != -1:
            ret['HWaddr'] = netcard_info[index+7: index+24].strip()
        index = netcard_info.find('inet addr')
        if index != -1:
            ret['inet_addr'] = netcard_info[index+10: index+10+netcard_info[index+10:].find(' ')].strip()
        index = netcard_info.find('Bcast')
        if index != -1:
            ret['Bcast'] = netcard_info[index+6: index+6+netcard_info[index+6:].find(' ')].strip()
        index = netcard_info.find('Mask')
        if index != -1:
            ret['Mask'] = netcard_info[index+5: index+5+netcard_info[index+5:].find(' ')].strip()
        return ret

    for i in res:
        for card in cards:
            if card in i:
                card_name = i[:i.find(' ')].strip()
                dd['card'][card_name] = get_field(i)

    return dd


# **********************************************************************************
# psutil获取机器的runtime信息
# **********************************************************************************


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
        'machine_info': machine_info(),
        'os_distribution': '-'.join(platform.linux_distribution()),
        'os_verbose': platform.platform(),
        'cpu_info': cpu_info(),
        'disk_size': '%sG' % disk_size(),
        'core_num': psutil.cpu_count(logical=False) or 0,
        'logic_num': psutil.cpu_count(logical=True),
        'memory_total': memory()['total'],
        'uptime': datetime.datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S'),
    }


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
        'swapped_in': sm.sin,
        'swapped_out': sm.sout
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


def cpu_cores():
    """ 每个cpu核心的信息
    :rtype list[OrderedDict]
    """
    return [c._asdict() for c in psutil.cpu_times_percent(0, percpu=True)]


def disk_total():
    disk_data = disks(all_partitions=True)
    space_total = sum([i['total'] for i in disk_data])
    space_used = sum([i['used'] for i in disk_data])
    return {
        'total': space_total,
        'used': space_used,
        'free': sum([i['free'] for i in disk_data]),
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


def process(pid):
    p = psutil.Process(pid)
    mem = p.memory_info_ex()
    cpu_times = p.cpu_times()
    # psutil throws a KeyError when the uid of a process is not associated with an user.
    try:
        username = p.username()
    except KeyError:
        username = None

    return {
        'pid': p.pid,
        'ppid': p.ppid(),
        'parent_name': p.parent().name() if p.parent() else '',
        'name': p.name(),
        'cmdline': ' '.join(p.cmdline()),
        'user': username,
        'uid_real': p.uids().real,
        'uid_effective': p.uids().effective,
        'uid_saved': p.uids().saved,
        'gid_real': p.gids().real,
        'gid_effective': p.gids().effective,
        'gid_saved': p.gids().saved,
        'status': p.status(),
        'created': p.create_time(),
        'terminal': p.terminal(),
        'mem_rss': mem.rss,
        'mem_vms': mem.vms,
        'mem_shared': mem.shared,
        'mem_text': mem.text,
        'mem_lib': mem.lib,
        'mem_data': mem.data,
        'mem_dirty': mem.dirty,
        'mem_percent': p.memory_percent(),
        'cwd': p.cwd(),
        'nice': p.nice(),
        'io_nice_class': p.ionice()[0],
        'io_nice_value': p.ionice()[1],
        'cpu_percent': p.cpu_percent(0),
        'num_threads': p.num_threads(),
        'num_files': len(p.open_files()),
        'num_children': len(p.children()),
        'num_ctx_switches_invol': p.num_ctx_switches().involuntary,
        'num_ctx_switches_vol': p.num_ctx_switches().voluntary,
        'cpu_times_user': cpu_times.user,
        'cpu_times_system': cpu_times.system,
        'cpu_affinity': p.cpu_affinity()
    }


def process_limits(pid):
    p = psutil.Process(pid)
    return {
        'RLIMIT_AS': p.rlimit(psutil.RLIMIT_AS),
        'RLIMIT_CORE': p.rlimit(psutil.RLIMIT_CORE),
        'RLIMIT_CPU': p.rlimit(psutil.RLIMIT_CPU),
        'RLIMIT_DATA': p.rlimit(psutil.RLIMIT_DATA),
        'RLIMIT_FSIZE': p.rlimit(psutil.RLIMIT_FSIZE),
        'RLIMIT_LOCKS': p.rlimit(psutil.RLIMIT_LOCKS),
        'RLIMIT_MEMLOCK': p.rlimit(psutil.RLIMIT_MEMLOCK),
        'RLIMIT_MSGQUEUE': p.rlimit(psutil.RLIMIT_MSGQUEUE),
        'RLIMIT_NICE': p.rlimit(psutil.RLIMIT_NICE),
        'RLIMIT_NOFILE': p.rlimit(psutil.RLIMIT_NOFILE),
        'RLIMIT_NPROC': p.rlimit(psutil.RLIMIT_NPROC),
        'RLIMIT_RSS': p.rlimit(psutil.RLIMIT_RSS),
        'RLIMIT_RTPRIO': p.rlimit(psutil.RLIMIT_RTPRIO),
        'RLIMIT_RTTIME': p.rlimit(psutil.RLIMIT_RTTIME),
        'RLIMIT_SIGPENDING': p.rlimit(psutil.RLIMIT_SIGPENDING),
        'RLIMIT_STACK': p.rlimit(psutil.RLIMIT_STACK)
    }


def process_environment(pid):
    with open('/proc/%d/environ' % pid) as f:
        contents = f.read()
        env_vars = dict(row.split('=', 1) for row in contents.split('\0') if '=' in row)
    return env_vars


def process_threads(pid):
    threads = []
    proc = psutil.Process(pid)
    for t in proc.threads():
        thread = {
            'id': t.id,
            'cpu_time_user': t.user_time,
            'cpu_time_system': t.system_time,
        }
        threads.append(thread)
    return threads


def process_open_files(pid):
    proc = psutil.Process(pid)
    return [f._asdict() for f in proc.open_files()]


def process_connections(pid):
    proc = psutil.Process(pid)
    conns = []
    for c in proc.connections(kind='all'):
        conn = {
            'fd': c.fd,
            'family': SOCKET_FAMILIES[c.family],
            'type': SOCKET_TYPES[c.type],
            'local_addr_host': c.laddr[0] if c.laddr else None,
            'local_addr_port': c.laddr[1] if c.laddr else None,
            'remote_addr_host': c.raddr[0] if c.raddr else None,
            'remote_addr_port': c.raddr[1] if c.raddr else None,
            'state': c.status
        }
        conns.append(conn)

    return conns


def process_memory_maps(pid):
    return [m._asdict() for m in psutil.Process(pid).memory_maps()]


def process_children(pid):
    proc = psutil.Process(pid)
    children = []
    for c in proc.children():
        child = {
            'pid': c.pid,
            'name': c.name(),
            'cmdline': ' '.join(c.cmdline()),
            'status': c.status()
        }
        children.append(child)

    return children


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
# Marmot
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


REDIS_HOST = '192.168.162.91'
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
        os.makedirs(to_dir)
    zfobj = zipfile.ZipFile(filename)
    for name in zfobj.namelist():
        if name.endswith('/'):
            path = os.path.join(to_dir, name)
            if not os.path.exists(path):
                os.makedirs(path)
        else:
            ext_filename = os.path.join(to_dir, name)
            ext_dir = os.path.dirname(ext_filename)
            if not os.path.exists(ext_dir):
                os.makedirs(ext_dir)
            outfile = open(ext_filename, 'wb')
            outfile.write(zfobj.read(name))
            outfile.close()


def backup_dir(dirname):
    dt = time.strftime('%Y-%m-%d-%H-%M-%S')
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
        return '{} :: '.format(time.strftime('%Y-%m-%d %H:%M:%S'))

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
        self.log('开始下载文件: %s ...' % self._pkg_url)
        try:
            filename = self.download_file()
        except IOError as e:
            logger.exception('Download file fail: %s' % self._pkg_url)
            self.log(str(e))
            return
        logger.info('Success to download file: %s' % self._pkg_url)
        self.log('下载完成: %s' % self._pkg_url)
        return filename


class TaskIceDeploy(TaskDownloadFile):
    def __init__(self, node_name, name, identifier, priority, pkg_url, pkg_dest_path):
        super(TaskIceDeploy, self).__init__(name, identifier, priority, pkg_url, pkg_dest_path)
        self.node_name = node_name.encode('utf-8')

    def header(self):
        return '{0} :: {1} :: '.format(self.node_name, time.strftime('%Y-%m-%d %H:%M:%S'))

    def deploy(self, filename):
        if os.path.exists(self._pkg_dest_path):
            self.log('开始备份旧版本文件...')
            backup_dir(self._pkg_dest_path)
            clear_dir(self._pkg_dest_path)
            self.log('备份完成!')
        else:
            self.log('创建工程目录:%s' % self._pkg_dest_path)
            os.makedirs(self._pkg_dest_path)
        self.log('开始解压zip文件到工程目录...')
        unzip(filename, self._pkg_dest_path)
        self.log('解压zip文件到工程目录--完成')
        self.log('>>>>>>>>>>>>>>>>完成<<<<<<<<<<<<<<<<<<')

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
        }

    @staticmethod
    def get_processes_info():
        return process_list()


class MarmotAgent(object):
    BIND_HOST = '0.0.0.0'
    PORT = 9001
    SYNC_INTERVAL = 2
    REMOTE_HOST = ''
    CONF_URL = 'http://192.168.162.91:8100/assets/server/conf/'
    DEFAULT_CONF = {
        'alarm_url': 'http://192.168.162.91:8100/alarm/',
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
        config = cls.handle_commandline()
        try:
            RDS.keys()
        except redis.RedisError:
            logger.error('Redis: ConnectionError')
            raise
        local_ip = get_local_ip()
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
