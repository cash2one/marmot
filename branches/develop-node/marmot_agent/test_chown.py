#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import grp
import pwd
import stat
import shutil

print pwd.getpwnam('baixue').pw_uid
print pwd.getpwnam('baixue').pw_gid
print grp.getgrnam("baixue").gr_gid


base_dir = os.path.dirname(__file__)


os.chmod('/home/baixue/temp/esmd5', 0755)  # 8进制
# os.chown('/home/baixue/temp/esmd5', pwd.getpwnam('nginx').pw_uid, pwd.getpwnam('nginx').pw_gid)

for top, _, fs in os.walk('/home/baixue/temp/esmd5'):
    os.chmod(top, 0777)
    for f in fs:
        os.chmod(os.path.join(top, f), 0666)
