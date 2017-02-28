#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import pprint
from kazoo.client import KazooClient


class ZKTestCase(unittest.TestCase):

    def setUp(self):
        self.zk = KazooClient(hosts='192.168.162.113:2181,192.168.162.114:2181,192.168.162.115:2181', timeout=5)
        self.zk.start()

    def test_es(self):
        hbase_nodes = self.zk.get_children("/hbase/rs")
        self.assertIsNotNone(hbase_nodes)
        pprint.pprint(hbase_nodes)

    def test_node(self):
        hbase_nodes = self.zk.get("/hbase/rs")
        self.assertIsNotNone(hbase_nodes)
        pprint.pprint(hbase_nodes)

    def test_get_node_info(self):
        print self.zk.get("/hbase/rs/dev-m162p112,16020,1471950060009")

    def tearDown(self):
        self.zk.stop()


if __name__ == '__main__':
    unittest.main()
