#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import time

import pexpect
import ptyprocess

# p = ptyprocess.PtyProcess.spawn(['redis-cli'])
# time.sleep(1)
# print p.read(1024)
# p.write('set baixue 666\n')
# time.sleep(1)
# print p.read(1024)
# time.sleep(1)
# print p.read(1024)


child = pexpect.spawn('hbase', ['shell'])
i = child.expect(['hbase\(main\).+?>', pexpect.EOF, pexpect.TIMEOUT], timeout=10)
print i
if i == 0:
    print 'success'
else:
    print 'fail'

child.sendline("status 'simple'")
i = child.expect(['hbase\(main\).+?>', pexpect.EOF, pexpect.TIMEOUT], timeout=10)
print i
if i == 0:
    print 'before:'
    print child.before
    print 'success'
else:
    print 'fail'

child.sendline('quit')
i = child.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=3)
print i
if i == 0:
    print 'quit success'
else:
    print 'quit fail'

child.close()

# pattern = re.compile(r'hbase\(main\).+?>')
#
# print re.match(pattern, 'hbase(main):001:10>')
