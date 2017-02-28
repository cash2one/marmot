# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import urllib
import urllib2
import json
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


logger = logging.getLogger('marmot')


def http_get_json(url, param=None):
    if param:
        url = url + '?' + urllib.urlencode(param)
    req = urllib2.Request(url)
    resp = urllib2.urlopen(req)
    return json.loads(resp.read())


class MarmotAuthBackend(ModelBackend):
    """
    Marmot authentication backend
    """
    cas_auth_url = settings.CAS_AUTH_URL

    def verify_ticket(self, ticket):
        try:
            resp = http_get_json(self.cas_auth_url, param={'ticket': ticket})
            if resp.get('status') == 'success':
                return resp.get('username')
        except Exception:
            logger.exception('CAS Validate')

    def authenticate(self, username=None, password=None, ticket=None, **kwargs):
        """
        Verify CAS ticket/Default ModelBackend and get User object
        """
        User = get_user_model()
        if ticket:
            username = self.verify_ticket(ticket)
            try:
                user = User.objects.get(username=username)
                return user
            except User.DoesNotExist:
                return None
        else:
            user = super(MarmotAuthBackend, self).authenticate(username, password, **kwargs)
            return user

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
