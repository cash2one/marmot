# -*- coding: utf-8 -*-
from __future__ import division
import time
from array import array

import psutil
import sysinfo


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
    def __init__(self, host, alarm_interval=10):
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
    def __init__(self, host, alarm_interval=10):
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
    def __init__(self, host, level=80, alarm_interval=10):
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
        for disk in sysinfo.disks():
            if disk['percent'] >= self._alarm_level:
                return Alarm(
                    self.host, 2, 'disk',
                    '{0}: 硬盘挂载点: {1}, 使用已经达到{2}%'.format(self.host, disk['mountpoint'], disk['percent'])
                )


class MonitorPort(BaseMonitor):
    """
    Port监视器
    """
    def __init__(self, host, alarm_interval=10):
        super(MonitorPort, self).__init__(host, alarm_interval=alarm_interval)
        self.allow_ports = set()  # 监听的端口
        self.deny_ports = set()  # 开放的端口 - 不允许被占用

    def set_allow_ports(self, ports):
        self.allow_ports = set(ports)

    def set_deny_ports(self, ports):
        self.deny_ports = set(ports)

    def get_alarm(self):
        listening_ports = sysinfo.listening_port_set()

        if self.allow_ports:
            if not (self.allow_ports < listening_ports):
                not_ports = self.allow_ports - listening_ports  # 监控端口列表中,没有被listen的端口
                return Alarm(self.host, 2, 'port', '{0}: 监听端口{1}没有被监听'.format(self.host, not_ports))

        if self.deny_ports:
            tmp = self.deny_ports & listening_ports
            if tmp:
                return Alarm(self.host, 2, 'port', '{0}: 开放端口{1}被占用'.format(self.host, tmp))
