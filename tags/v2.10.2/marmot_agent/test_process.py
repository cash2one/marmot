import subprocess
import psutil


def kill_process(pname):
    for p in psutil.process_iter():
        if pname in p.cmdline():
            p.kill()


def start_process(cmd):
    popen = subprocess.Popen([cmd], stdout=subprocess.PIPE)
    return popen.pid
    # subprocess.call()
    # os.system()
