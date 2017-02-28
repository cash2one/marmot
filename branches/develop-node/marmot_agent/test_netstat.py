#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import subprocess


def netstat(port, sudo=None):
    try:
        return subprocess.check_output('netstat -an | grep %s' % port, shell=True)
    except subprocess.CalledProcessError:
        return ''


if __name__ == '__main__':
    print netstat(8100)
