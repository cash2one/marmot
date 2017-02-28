#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
from gevent import monkey; monkey.patch_all()
from gevent import subprocess

import os
import pwd
import urllib
import time
import sys

# os.chmod()
# os.chown()
# os.umask()
# os.setgid()
# os.setuid()
# os.getgid()
# os.getuid()

# print subprocess.check_output(['/home/baixue/note/shell/progress.sh'])


def start():
    st = time.time()
    proc = subprocess.Popen(
            ['/opt/SpringCloud/bin/hx-ribbon.sh start'], cwd='/opt/SpringCloud/bin/',
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
        )

    ret, out = proc.communicate()
    print ret
    print out
    print time.time() - st


def stop():
    st = time.time()
    proc = subprocess.Popen(
            ['/opt/SpringCloud/bin/hx-ribbon.sh stop'], cwd='/opt/SpringCloud/bin/',
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
        )

    ret, out = proc.communicate()
    print ret
    print out
    print time.time() - st

if sys.argv[1] == 'start':
    start()
else:
    stop()

# resp = urllib.urlopen("http://{0}:{1}/ping".format('192.168.23.121', 18001))
# res = resp.read()
# resp.close()
#
# print res
# print 'pong' in res
