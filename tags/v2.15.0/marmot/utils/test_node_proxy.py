# -*- coding: utf-8 -*-
import unittest
from node_proxy import NodeProxy


class NodeProxyTestCase(unittest.TestCase):
    def setUp(self):
        self.node1 = NodeProxy('192.168.162.181', 9001)
        self.node2 = NodeProxy('localhost', 9001)

    def test_is_alive(self):
        self.assertTrue(self.node1.is_alive())
        self.assertRaises(IOError, self.node2.is_alive)

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
