import os
import time


def backup_database(host, port, user, pwd, db):
    bak = 'bak-{0}-{1}'.format(db, time.strftime('%Y-%m-%d-%H-%M-%S'))
    cmd = 'mysqldump -h{host} --port={port} -u{user} --password={pwd} {db} > {bak}.sql;'.format(
        host=host, port=port, user=user, pwd=pwd, db=db, bak=bak
    )
    return os.system(cmd)


def execute_sql(host, port, user, pwd, db, sql):
    cmd = 'mysql -h{host} --port={port} -u{user} --password={pwd} {db} < {sql};'.format(
        host=host, port=port, user=user, pwd=pwd, db=db, sql=sql
    )
    return os.system(cmd)


if __name__ == '__main__':
    print backup_database('localhost', 3306, 'root', 'xuebailove321', 'marmot')
