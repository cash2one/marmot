#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
from gevent import subprocess

import os
import sys
import fcntl
import time
import signal
import tempfile

"""
如果用gevent.subprocess去启动子进程, 那么如果主进程结束, 子进程也会结束
"""


def startup_node_app1():
    cwd = '/home/baixue/idea/node/'
    try:
        proc = subprocess.Popen(
                ['node', 'app.js'], cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
    except OSError as e:
        return -1, str(e)

    gevent.sleep(0.2)

    if proc.poll() is not None:
        # 如果进程还在运行,  poll()返回None
        # 如果进程已经结束返回retcode
        out = proc.stdout.read()
        proc.stdout.close()
        return -1, out

    # TODO 用fcntl将pipe设置成非阻塞读取, 对gevent不管用
    # fcntl.fcntl(proc.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
    # fd = proc.stdout.fileno()
    # fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    # fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    out = []
    def _read_out():
        while True:
            line = proc.stdout.readline()
            out.append(line)
            gevent.sleep(0)
            if proc.poll() is not None:
                break
    stdout = gevent.spawn(_read_out)

    if stdout.join(timeout=3.0) is None:
        # 如果join超时, 返回None
        stdout.kill()
        # pipe = proc.stdout
        # proc.stdout = os.tmpfile()
        # pipe.close()  # TODO 关闭pipe管道, 启动的node程序会因为写不进stdout而死掉
        return proc.pid, '\n'.join(out)
    else:
        return -1, 'Startup Failed'


def startup_node_app2():
    cwd = '/home/baixue/idea/node/'
    app = 'nodeapp'
    try:
        logpath = tempfile.mktemp(suffix='.log', prefix=app)
        proc = subprocess.Popen(
                ['node', 'app.js'], cwd=cwd,
                stdout=open(logpath, 'w'), stderr=subprocess.STDOUT
            )
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


for i in startup_node_app2():
    print i
    print

gevent.signal(signal.SIGQUIT, gevent.kill)
