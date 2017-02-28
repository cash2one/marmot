#!/usr/bin/env python
# -*- coding: utf-8 -*-
import socket
import datetime
import pprint
import psutil

from marmot import users, memory, swap_memory, disks, disk_total, cpu


print '------ users ------'
pprint.pprint(users())

print '------ memory ------'

memory_data = memory()

print '------ swap_memory ------'
pprint.pprint(swap_memory())

print '------ disks ------'
pprint.pprint(disks())

print '------ disk_total ------'
pprint.pprint(disk_total())

print '------ cpu ------'
pprint.pprint(cpu())

print '------ connections ------'
pprint.pprint(connections())




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

data = get_runtime_info()

print '-----------------------------------'
pprint.pprint(data)
