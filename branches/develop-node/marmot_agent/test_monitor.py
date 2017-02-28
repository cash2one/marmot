#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division

import gevent
from gevent import monkey; monkey.patch_all()

from marmot import (
    listening_port_set, BaseMonitor, Alarm,
    ProcessMonitor, CpuMonitor, MemoryMonitor, DiskMonitor
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
