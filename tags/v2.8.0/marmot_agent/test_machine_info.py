# -*- coding: utf-8 -*-
import os
import re
import fcntl
import socket
import struct
import cStringIO
import subprocess
from uuid import getnode as get_mac
from collections import OrderedDict, namedtuple
import netifaces


def get_HwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
    return ':'.join(['%02x' % ord(char) for char in info[18:24]])


def get_mac_addr():
    mac = get_mac()
    return ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))


def run_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = p.communicate()[0]
    return output


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


def cpu_info_():
    vendor_pattern = re.compile(r'vendor_id([\ \t])+\:\ (?P<vendor_id>.*)\n')
    model_pattern = re.compile(r'model\ name([\ \t])+\:\ (?P<model_name>.*)\n')
    f = open('/proc/cpuinfo')
    content = f.read()
    f.close()
    return {
        'vendor': re.search(vendor_pattern, content).group('vendor_id').strip(),
        'model': re.search(model_pattern, content).group('model_name').strip(),
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


def netcard_info_():
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


def netcard_info():
    interfaces = netifaces.interfaces()
    ret = {}
    for i in interfaces:
        if 'eth' not in i:
            continue
        netcard = netifaces.ifaddresses(i)[netifaces.AF_INET][0]
        ret[i] = {
            'mac': get_HwAddr(i),
            'broadcast': netcard['broadcast'],
            'mask': netcard['netmask'],
            'addr': netcard['addr'],
        }
    return ret


if __name__ == '__main__':
    # import time
    # st = time.time()
    # print machine_info()
    # print time.time() - st
    # print
    import time
    st = time.time()
    print netcard_info()
    print time.time() - st
    # print
    # print disk_size()
    # print
    # print netcard_info()
