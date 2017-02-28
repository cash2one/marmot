#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
from gevent import monkey; monkey.patch_all()
from gevent.queue import Queue, Empty


class Actor(gevent.Greenlet):

    def __init__(self, interval):
        self.inbox = Queue()
        self._interval = interval
        self._timeout = None
        super(Actor, self).__init__()

    def work(self):
        """
        Define in your subclass.
        """
        raise NotImplemented()

    def _run(self):
        while True:
            try:
                msg = self.inbox.get(block=True, timeout=self._timeout)
                if msg == 'stop':
                    self._timeout = None
                elif msg == 'start':
                    self._timeout = self._interval
                elif msg == 'shutdown':
                    break
            except Empty:
                self.work()
            gevent.sleep(0)

    def start(self):
        self.inbox.put('start')
        return super(Actor, self).start()

    def stop(self):
        self.inbox.put('stop')

    def shutdown(self):
        self.inbox.put('shutdown')


class Pinger(Actor):
    
    def __init__(self, name, interval):
        self.name = name
        super(Pinger, self).__init__(interval)

    def work(self):
        print(self.name)


class Ponger(Pinger):
    def work(self):
        print(self.name)


ping = Pinger('AAAAAAA', 1)
pong = Ponger('BBBBBBB', 1)

ping.start()
pong.start()

ping.start()
pong.start()

gevent.sleep(5)

ping.stop()
pong.stop()

gevent.sleep(5)

ping.start()
pong.start()

gevent.sleep(5)

ping.shutdown()
pong.shutdown()

gevent.joinall([ping, pong])
