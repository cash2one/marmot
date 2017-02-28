#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import psutil


def kill_process(cmd):
    cmd_flag = os.path.sep.join(cmd.split(os.path.sep)[:3])
    for p in psutil.process_iter():
        if cmd_flag in ''.join(p.cmdline()):
            print cmd_flag
            print ''.join(p.cmdline())
            print p.pid
    return False


if __name__ == '__main__':
    kill_process('/opt/tomcat_haina/bin/startup.sh')
