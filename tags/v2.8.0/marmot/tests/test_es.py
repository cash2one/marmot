#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import json
import pprint
import requests


class ESTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def test_es(self):
        res1 = requests.get('http://192.168.162.91:9201/_cluster/health?pretty')
        res2 = requests.get('http://192.168.162.91:9202/_cluster/health?pretty')
        pprint.pprint(json.loads(res1.text))
        pprint.pprint(json.loads(res2.text))
        self.assertIsNotNone(res1.text)
        self.assertIsNotNone(res2.text)

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
