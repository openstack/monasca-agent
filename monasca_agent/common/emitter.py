# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from hashlib import md5
import json
from urllib.error import HTTPError
from urllib.request import build_opener
from urllib.request import ProxyHandler
from urllib.request import Request


def post_headers(payload):
    return {
        'User-Agent': 'Mon/Agent',
        'Content-Type': 'application/json',
        'Accept': 'text/html, */*',
        'Content-MD5': md5(payload).hexdigest()
    }


def http_emitter(message, log, url):
    """Send payload
    """

    log.debug('http_emitter: attempting postback to ' + url)

    # Post back the data
    partial_payload = []
    for measurement in message:
        partial_payload.append(measurement)

    payload = json.dumps(partial_payload)
    payload = payload.encode('utf-8')
    url = "%s/intake" % url
    headers = post_headers(payload)

    try:
        # Make sure no proxy is autodetected for this localhost connection
        proxy_handler = ProxyHandler({})
        # Should this be installed as the default opener and reused?
        opener = build_opener(proxy_handler)
        request = Request(url, payload, headers)
        response = None
        try:
            response = opener.open(request)
            log.debug('http_emitter: postback response: ' + str(response.read()))
        except Exception as exc:
            log.error("""Forwarder at {0} is down or not responding...
                      Error is {1}
                      Please restart the monasca-agent.""".format(url, repr(exc)))
        finally:
            if response:
                response.close()
    except HTTPError as e:
        if e.code == 202:
            log.debug("http payload accepted")
        else:
            raise
