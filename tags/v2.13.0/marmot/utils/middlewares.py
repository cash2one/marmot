# -*- coding: utf-8 -*-
from time import time
from logging import getLogger


class LoggingMiddleware(object):
    def __init__(self):
        # arguably poor taste to use django's logger
        self.logger = getLogger('marmot')

    def process_request(self, request):
        request.timer = time()
        return None

    def process_response(self, request, response):
        if 'HTTP_X_FORWARDED_FOR' in request.META:
            remote_ip = request.META['HTTP_X_FORWARDED_FOR']
        else:
            remote_ip = request.META['REMOTE_ADDR']
        self.logger.info(
            ' [%s] %s %s [%s] (%.1fs)',
            remote_ip,
            request.method,
            request.get_full_path(),
            response.status_code,
            time() - request.timer
        )
        return response
