#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import pprint

import redis
from rediscluster.cluster_mgt import RedisClusterMgt
from rediscluster import StrictRedisCluster


class RedisClusterTestCase(unittest.TestCase):

    def setUp(self):
        self.rc = StrictRedisCluster(
            startup_nodes=[{"host": "192.168.162.90", "port": "7380"},
                           {"host": "192.168.162.90", "port": "7381"},
                           {"host": "192.168.162.90", "port": "7382"},
                           {"host": "192.168.162.91", "port": "7380"},
                           {"host": "192.168.162.91", "port": "7381"},
                           {"host": "192.168.162.91", "port": "7382"}]
        )

    def test_info(self):
        pprint.pprint(self.rc.info())

    def tearDown(self):
        pass


class RedisClusterMgtTestCase(unittest.TestCase):

    def setUp(self):
        self.rc = RedisClusterMgt(
            startup_nodes=[{"host": "192.168.162.90", "port": "7380"},
                           {"host": "192.168.162.90", "port": "7381"},
                           {"host": "192.168.162.90", "port": "7382"},
                           {"host": "192.168.162.91", "port": "7380"},
                           {"host": "192.168.162.91", "port": "7381"},
                           {"host": "192.168.162.91", "port": "7382"}]
        )

    def test_info(self):
        pprint.pprint(self.rc.info())

    def test_nodes(self):
        pprint.pprint(self.rc.nodes())

    def tearDown(self):
        pass


class RedisMonitorTestCase(unittest.TestCase):

    def setUp(self):
        self.r = redis.StrictRedis(host='192.168.162.90', port=7381)

    def test_node_info(self):
        info = self.r.info()
        pprint.pprint(info)
        self.assertIsNotNone(info)

    def test_node_memory_info(self):
        memory_info = self.r.info(section='memory')
        pprint.pprint(memory_info)
        self.assertIsNotNone(memory_info)

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
