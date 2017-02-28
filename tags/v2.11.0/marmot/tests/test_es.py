#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib
import urllib2
import json
import pprint
import unittest


def http_get_json(url, param=None):
    if param:
        url = url + '?' + urllib.urlencode(param)
    req = urllib2.Request(url)
    res = urllib2.urlopen(req)
    return json.loads(res.read())


class ESTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def test_es(self):
        req1 = urllib2.Request('http://localhost:9201/_cluster/health?pretty')
        req2 = urllib2.Request('http://localhost:9202/_cluster/health?pretty')
        resp1 = urllib2.urlopen(req1)
        resp2 = urllib2.urlopen(req2)
        print 'resp1'
        pprint.pprint(json.loads(resp1.read()))
        print 'resp2'
        pprint.pprint(json.loads(resp2.read()))
        self.assertIsNotNone(resp1)
        self.assertIsNotNone(resp2)

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
