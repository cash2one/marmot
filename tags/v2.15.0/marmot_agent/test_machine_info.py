# -*- coding: utf-8 -*-
import os
import cStringIO
import subprocess
from uuid import getnode as get_mac
from collections import namedtuple

from marmot import cpu_info, netcard_info


def get_mac_addr():
    mac = get_mac()
    return ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))


def run_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = p.communicate()[0]
    return output


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


usage_ntuple = namedtuple('usage',  'total used free percent')


def disk_usage(path):
    """Return disk usage associated with path."""
    st = os.statvfs(path)
    free = (st.f_bavail * st.f_frsize)
    total = (st.f_blocks * st.f_frsize)
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    try:
        percent = (float(used) / total) * 100
    except ZeroDivisionError:
        percent = 0
    return usage_ntuple(total, used, free, round(percent, 1))


if __name__ == '__main__':
    # import time
    # st = time.time()
    # print machine_info()
    # print time.time() - st
    # print
    import time
    st = time.time()
    print cpu_info()
    print time.time() - st
    # print
    # print disk_size()
    # print
    # print netcard_info()
