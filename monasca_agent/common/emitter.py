# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP

from hashlib import md5
import json
import urllib2


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
    url = "%s/intake" % url
    headers = post_headers(payload)

    try:
        # Make sure no proxy is autodetected for this localhost connection
        proxy_handler = urllib2.ProxyHandler({})
        # Should this be installed as the default opener and reused?
        opener = urllib2.build_opener(proxy_handler)
        request = urllib2.Request(url, payload, headers)
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
    except urllib2.HTTPError as e:
        if e.code == 202:
            log.debug("http payload accepted")
        else:
            raise
