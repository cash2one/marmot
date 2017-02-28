# -*- coding: utf-8 -*-
import unittest
import pprint
import icegridadmin


class IceGridAdminTestCase(unittest.TestCase):
    def setUp(self):
        self.admin = icegridadmin.IceGridAdmin(
            'admin', 'beijing', 'icegridadmin',
            prefix='BrIceGrid',
            master_ip='192.168.162.181', master_port='4061',
            slave_ip='192.168.162.182', slave_port='4061'
        )
        # admin = IceGridAdmin(
        #     'admin', 'qazwsx', 'icegridadmin',
        #     prefix='BrIceGrid',
        #     master_ip='192.168.23.111', master_port='4061',
        #     slave_ip='192.168.23.112', slave_port='4061'
        # )
        self.admin.initialize()

    def test_get_all_registry_names(self):
        names = self.admin.get_all_registry_names()
        self.assertIsInstance(names, list)
        pprint.pprint(names)

    def test_ping_registry(self):
        names = self.admin.get_all_registry_names()
        for name in names:
            self.assertTrue(self.admin.ping_registry(name))

        # IceGrid::RegistryNotExistException
        self.assertRaises(icegridadmin.RegistryNotExistException, self.admin.ping_registry, 'error-registry')

    def test_get_registry_info(self):
        names = self.admin.get_all_registry_names()
        for name in names:
            registry_info = self.admin.get_registry_info(name)
            print registry_info

    def test_get_all_node_names(self):
        nodes = self.admin.get_all_node_names()
        self.assertIsInstance(nodes, list)
        pprint.pprint(nodes)

    def test_get_node_info(self):
        nodes = self.admin.get_all_node_names()
        for node in nodes:
            info = self.admin.get_node_info(node)
            pprint.pprint(info)

    def test_get_all_server_ids(self):
        ids = self.admin.get_all_server_ids()
        self.assertIsInstance(ids, list)
        pprint.pprint(ids)

    def test_get_server_pid(self):
        ids = self.admin.get_all_server_ids()
        for i in ids:
            pid = self.admin.get_server_pid(i)
            print i
            print type(pid)
            print pid

    def test_get_server_state(self):
        ids = self.admin.get_all_server_ids()
        for i in ids:
            state = self.admin.get_server_state(i)
            print i
            print state

    def test_get_server_info(self):
        ids = self.admin.get_all_server_ids()
        for i in ids:
            info = self.admin.get_server_info(i)
            print i
            print info

    def test_get_all_application_names(self):
        apps = self.admin.get_all_application_names()
        self.assertIsInstance(apps, list)
        pprint.pprint(apps)

    def test_get_application_info(self):
        info = self.admin.get_application_info('AppAlarm')
        print type(info)
        print info

    def tearDown(self):
        self.admin.destroy()


if __name__ == '__main__':
    unittest.main()
