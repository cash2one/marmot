#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division

import gevent
from gevent import monkey; monkey.patch_all()
from gevent.queue import Queue, Empty

import json
import time
import urllib
import urllib2
from array import array

import psutil

from marmot import disks, listening_port_set


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
        self.timeout = interval

    def work(self):
        """
        Define in your subclass.
        """
        raise NotImplemented()

    def _run(self):
        while True:
            try:
                msg = self._inbox.get(block=True, timeout=self.timeout)
                if msg == 'stop':
                    self.timeout = None
                elif msg == 'start':
                    self.timeout = self._interval
                elif msg == 'shutdown':
                    break
            except Empty:
                self.work()

    def start(self):
        self._inbox.put('start')
        return super(Actor, self).start()

    def stop(self):
        self._inbox.put('stop')

    def shutdown(self):
        self._inbox.put('shutdown')


class BaseMonitor(Actor):
    alarm_url = ''

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
        url = self.alarm_url + '?' + urllib.urlencode(alarm.message())
        req = urllib2.Request(url)
        res = urllib2.urlopen(req)
        return json.loads(res.read())

    def get_alarm(self):
        raise NotImplementedError

    def work(self):
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
    def __init__(self, name, host, process, port, alarm_interval=20):
        super(ProcessMonitor, self).__init__(host, alarm_interval=alarm_interval, name=name)
        self.process = process
        self.port = port

    def check_process(self):
        for p in psutil.process_iter():
            if self.process in ''.join(p.cmdline()):
                return True
        return False

    def check_port(self):
        if self.port in listening_port_set():
            return True
        return False

    def get_alarm(self):
        print self.name
        if not self.check_process():
            return Alarm(self.host, 'process', '进程: {0}未存活'.format(self.process), level=3)
        if not self.check_port():
            return Alarm(self.host, 'port', '端口: {0}未被占用'.format(self.port), level=3)


class CpuMonitor(BaseMonitor):
    """
    Cpu负载监视器
    """
    def __init__(self, host, alarm_interval=20):
        super(CpuMonitor, self).__init__(host, work_interval=2, alarm_interval=alarm_interval)
        # 监控Actor的interval是2second, 这里缓冲1小时的数据, 即1800个数据
        self._buf = Buffer(1800)

    def load_avg(self):
        self._buf.append(psutil.cpu_percent())  # 刷新缓冲
        return {
            'avg10': self._buf.xmean(10 * 30),
            'avg30': self._buf.xmean(30 * 30),
            'avg60': self._buf.xmean(60 * 30),
        }

    def get_alarm(self):
        print self.name
        avg = self.load_avg()
        if avg['avg60'] >= 99.0:
            return Alarm(self.host, 'cpu', '{}: Cpu负载已经持续1小时超过99%'.format(self.host), level=3)
        if avg['avg30'] >= 99.0:
            return Alarm(self.host, 'cpu', '{}: Cpu负载已经持续30分钟超过99%'.format(self.host), level=2)
        if avg['avg10'] >= 99.0:
            return Alarm(self.host, 'cpu', '{}: Cpu负载已经持续10分钟超过99%'.format(self.host), level=1)


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
        print self.name
        self._buf.append(psutil.virtual_memory().percent)
        used = self._buf.mean()
        if used >= self._alarm_level:
            return Alarm(self.host, 'memory', '{0}: 内存使用已经达到{1}%'.format(self.host, used), level=2)


class DiskMonitor(MemoryMonitor):
    """
    Disk监视器
    """
    def get_alarm(self):
        print self.name
        for disk in disks():
            if disk['percent'] >= self._alarm_level:
                return Alarm(
                    self.host, 'disk',
                    '{0}: 硬盘挂载点: {1}, 使用已经达到{2}%'.format(self.host, disk['mountpoint'], disk['percent']),
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
        print self.name
        listening_ports = listening_port_set()

        if self.allow_ports:
            if not (self.allow_ports < listening_ports):
                not_ports = self.allow_ports - listening_ports  # 监控端口列表中,没有被listen的端口
                return Alarm(self.host, 'port', '{0}: 监听端口{1}没有被监听'.format(self.host, not_ports), level=2)

        if self.deny_ports:
            tmp = self.deny_ports & listening_ports
            if tmp:
                return Alarm(self.host, 'port', '{0}: 开放端口{1}被占用'.format(self.host, tmp), level=1)


class MonitorGroup(object):
    def __init__(self, host):
        self._monitors = {
            'CpuMonitor': CpuMonitor(host),
            'MemoryMonitor': MemoryMonitor(host),
            'DiskMonitor': DiskMonitor(host),
            'PortMonitor': PortMonitor(host),
        }

    def add_process_monitor(self, monitor):
        self._monitors[monitor.name] = monitor

    def remove_process_monitor(self, name):
        try:
            del self._monitors[name]
        except KeyError:
            pass

    def preview(self):
        return self._monitors.keys()

    def start(self):
        for m in self._monitors.values():
            m.start()

    def stop(self):
        for m in self._monitors.values():
            m.stop()

    def shutdown(self):
        for m in self._monitors.values():
            m.shutdown()
        gevent.joinall(self._monitors.values())

    def kill(self):
        for m in self._monitors.values():
            m.kill()


if __name__ == '__main__':

    monitor_group = MonitorGroup('localhost')

    monitor_group.add_process_monitor(ProcessMonitor('ProcessMonitor', 'localhost', 'mysqld', 3306))

    print monitor_group.preview()

    monitor_group.start()
    gevent.sleep(20)
    monitor_group.stop()
    gevent.sleep(20)
    monitor_group.start()
    gevent.sleep(20)
    monitor_group.shutdown()
