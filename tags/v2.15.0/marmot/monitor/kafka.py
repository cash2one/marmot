# -*- coding: utf-8 -*-
import json
import pprint

from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError
from kazoo.handlers.threading import KazooTimeoutError


class ZKKafka(object):
    """kafka zookeeper接口"""

    def __init__(self, hosts, timeout=5.0):
        self.zk = KazooClient(hosts=hosts, timeout=timeout)

    def start(self):
        self.zk.start()

    def get_ids(self):
        ids = self.zk.get_children("/brokers/ids")
        return ids

    def get_topics(self):
        topics = self.zk.get_children("/brokers/topics")
        return topics

    def get_topic_state(self, topic):
        info = json.loads(self.zk.get("/brokers/topics/{0}".format(topic))[0])
        state = []
        for partition, replicas in info['partitions'].items():
            partition_state = self.get_partition_state(topic, partition)
            state.append({
                'partition': partition,
                'replicas': replicas,
                'leader': partition_state['leader'],
                'isr': partition_state['isr'],
            })
        return state

    def get_partition_state(self, topic, partition):
        return json.loads(self.zk.get("/brokers/topics/{0}/partitions/{1}/state".format(topic, partition))[0])

    def get_all_topic_state(self):
        topics = {}
        for t in self.get_topics():
            topics[t] = self.get_topic_state(t)
        return topics

    def stop(self):
        self.zk.stop()


if __name__ == '__main__':
    kafka = ZKKafka('192.168.162.90:2181,192.168.162.91:2181,192.168.162.92:2181')

    try:
        kafka.start()
    except KazooTimeoutError:
        raise

    try:
        pprint.pprint(kafka.get_ids())
    except NoNodeError:
        raise

    pprint.pprint(kafka.get_all_topic_state())

    kafka.stop()
