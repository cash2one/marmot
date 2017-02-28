# -*- coding: utf-8 -*-
import os
import time
import subprocess
import unittest


def backup_database(host, port, user, passwd, db):
    proc = subprocess.Popen(
            ['mysqldump', '-h%s' % host, '--port=%s' % port,
             '-u%s' % user, '--password=%s' % passwd, db],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
    out, _ = proc.communicate()
    try:
        out = out[out.index(os.linesep)+1:]
    except ValueError:  # substring not found
        out = ''
    retcode = proc.poll()
    if retcode == 0:
        bak = os.path.join('/tmp/', 'bak-{0}-{1}.sql'.format(db, time.strftime('%Y%m%d%H%M%S')))
        f = open(bak, 'wb')
        f.write(out)
        f.close()
        return retcode, os.path.abspath(bak)
    else:
        return retcode, out


def execute_sql(host, port, user, passwd, db, sql):
    proc = subprocess.Popen(
            ['mysql', '--default-character-set=utf8', '-h', host,
             '--port=%s' % port, db, '-u', user, '--password=%s' % passwd],
            stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT
        )
    out, _ = proc.communicate('source ' + sql)
    try:
        out = out[out.index(os.linesep)+1:]
    except ValueError:  # substring not found
        out = ''
    retcode = proc.poll()
    return retcode, out


class DBTestCase(unittest.TestCase):

    def test_backup_database(self):
        print backup_database('localhost', 3306, 'root', 'xuebailove31', 'marmot')

    # def test_execute_sql(self):
    #     print execute_sql('localhost', 3306, 'root', 'xuebailove321', 'crm', '/home/baixue/temp/test.sql')


if __name__ == '__main__':
    unittest.main()
