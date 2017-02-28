#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
from gevent import subprocess

import pexpect


def hbase_status_simple2():
    child = pexpect.spawn('hbase', ['shell'])
    gevent.sleep(5)
    i = child.expect(['hbase\(main\).+?>', pexpect.EOF, pexpect.TIMEOUT], timeout=10)
    if i != 0:
        child.close(force=True)
        return 'HBaseShell Start Error'

    child.sendline("status 'simple'")
    gevent.sleep(0)
    i = child.expect(['hbase\(main\).+?>', pexpect.EOF, pexpect.TIMEOUT], timeout=10)
    if i != 0:
        child.close(force=True)
        return 'HBaseShell run "status simple" error'

    info = child.before

    child.sendline('quit')
    i = child.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=3)
    if i != 0:
        child.sendcontrol('c')
    child.close()
    return info


def hbase_status_simple():
    proc = subprocess.Popen(
            ['hbase', 'shell'], stdout=subprocess.PIPE,
            stdin=subprocess.PIPE, stderr=subprocess.STDOUT
        )
    print 'retcode:', proc.poll()
    out, _ = proc.communicate("status 'simple'\n")
    retcode = proc.poll()
    print 'retcode:', proc.poll()
    return retcode, out


class Service(object):
    """保持hbase shell子进程的会话"""
    def __init__(self):
        self.hb_shell = None

    def hbase_status_simeple(self):
        try:
            if self.hb_shell is None or self.hb_shell.poll() is not None:
                self.hb_shell = subprocess.Popen(
                        ['hbase', 'shell'], stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                    )

            self.hb_shell.stdin.write("status 'simple'\n")
            self.hb_shell.stdin.flush()
            gevent.sleep(0.1)

            self.out = ''
            def _read_out():
                while True:
                    line = self.hb_shell.stdout.readline()
                    self.out += line
                    if line.startswith('Aggregate load:'):
                        break
            stdout = gevent.spawn(_read_out)
            if stdout.join(timeout=10.0) is None:
                stdout.kill()
            return self.out
        except Exception as e:
            return 'Error: ' + str(e)


service = Service()
for i in xrange(60):
    print i
    print service.hbase_status_simeple()
    gevent.sleep(1.5)
