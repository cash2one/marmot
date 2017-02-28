#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest

from starbase import Connection


class HBaseTestCase(unittest.TestCase):

    def setUp(self):
        self.c = Connection(host='192.168.162.113', port=2181)

    def test_hbase(self):
        print self.c.cluster_version
        print self.c.cluster_status

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
