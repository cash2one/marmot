import unittest
from . import backup_database, execute_sql


class DBTestCase(unittest.TestCase):

    def test_backup_database(self):
        backup_database('localhost', 3306, 'root', 'xuebailove321', 'marmot')

    def test_execute_sql(self):
        execute_sql('localhost', 3306, 'root', 'xuebailove321', 'db', 'xxx.sql')


if __name__ == '__main__':
    unittest.main()
