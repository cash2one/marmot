# -*- coding: utf-8 -*-
import httplib
import xmlrpclib


class NodeProxyError(Exception):
    """
    IOError
    xmlrpclib.Fault
    httplib.BadStatusLine
    """
    pass


class TimeoutTransport(xmlrpclib.Transport):
    timeout = 12.0

    def set_timeout(self, timeout):
        self.timeout = timeout

    def make_connection(self, host):
        # return an existing connection if possible.  This allows
        # HTTP/1.1 keep-alive.
        if self._connection and host == self._connection[0]:
            return self._connection[1]

        # create a HTTP connection object from a host descriptor
        chost, self._extra_headers, x509 = self.get_host_info(host)
        # store the host argument along with the connection object
        self._connection = host, httplib.HTTPConnection(chost, timeout=self.timeout)
        return self._connection[1]


class TimeoutServerProxy(xmlrpclib.ServerProxy):
    def __init__(self, uri, timeout=10.0, *args, **kwargs):
        t = TimeoutTransport(use_datetime=kwargs.get('use_datetime', 0))
        t.set_timeout(timeout)
        kwargs['transport'] = t
        xmlrpclib.ServerProxy.__init__(self, uri, *args, **kwargs)


class NodeProxy(TimeoutServerProxy):
    def __init__(self, host, port, timeout=15.0, *args, **kwargs):
        TimeoutServerProxy.__init__(self, 'http://%s:%s' % (host, port), timeout=timeout, *args, **kwargs)
