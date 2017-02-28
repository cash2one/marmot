# -*- coding: utf-8 -*-
from __future__ import division
import os
import platform
import datetime
import socket

import psutil
import netifaces


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
        'machine_info': machine_info.machine_info(),
        'os_distribution': '-'.join(platform.linux_distribution()),
        'os_verbose': platform.platform(),
        'cpu_info': machine_info.cpu_info(),
        'disk_size': '%sG' % machine_info.disk_size(),
        'netcard_info': machine_info.netcard_info(),
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


if __name__ == '__main__':
    for i in disks():
        print i
