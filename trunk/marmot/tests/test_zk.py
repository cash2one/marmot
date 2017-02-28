#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import pprint
import json
from kazoo.client import KazooClient


class ZKHBaseCase(unittest.TestCase):
    """HBase"""

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


class ZKKafkaCase(unittest.TestCase):
    """kafka"""

    def setUp(self):
        self.zk = KazooClient(hosts='192.168.162.90:2181,192.168.162.91:2181,192.168.162.92:2181', timeout=5.0)
        self.zk.start()

    def test_root(self):
        root = self.zk.get_children("/")
        self.assertIsNotNone(root)
        pprint.pprint(root)

    def test_ids(self):
        ids = self.zk.get_children("/brokers/ids")
        self.assertIsNotNone(ids)
        pprint.pprint(ids)

    def test_topics(self):
        topics = self.zk.get_children("/brokers/topics")
        self.assertIsNotNone(topics)
        pprint.pprint(topics)

    def test_topic(self):
        topic = json.loads(self.zk.get("/brokers/topics/queue")[0])
        self.assertIsNotNone(topic)
        print topic['partitions']

    def test_partitions(self):
        partitions = self.zk.get("/brokers/topics/queue/partitions/0/state")
        self.assertIsNotNone(partitions)
        pprint.pprint(partitions)

    def tearDown(self):
        self.zk.stop()


if __name__ == '__main__':
    unittest.main()
