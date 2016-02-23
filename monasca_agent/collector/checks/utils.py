# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import base64


def add_basic_auth(request, username, password):
    """A helper to add basic authentication to a urllib2 request.

    We do this across a variety of checks so it's good to have this in one place.
    """
    auth_str = base64.encodestring('%s:%s' % (username, password)).strip()
    request.add_header('Authorization', 'Basic %s' % auth_str)
    return request
