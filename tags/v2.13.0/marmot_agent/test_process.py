import os
import subprocess
import psutil


def kill_process(cmd):
    cmd_flag = os.path.sep.join(cmd.split(os.path.sep)[:3])
    for p in psutil.process_iter():
        if cmd_flag in ''.join(p.cmdline()):
            print cmd_flag
            print ''.join(p.cmdline())
            print p.pid
    return False


def start_process(cmd):
    popen = subprocess.Popen([cmd], stdout=subprocess.PIPE)
    return popen.pid
    # subprocess.call()
    # os.system()
