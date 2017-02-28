#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
import pexpect


def hbase_status_simple():
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


print hbase_status_simple()
