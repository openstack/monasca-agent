from hashlib import md5
import json
import urllib2

from monagent.common.metrics import Measurement


def post_headers(agentConfig, payload):
    return {
        'User-Agent': 'Datadog Agent/%s' % agentConfig['version'],
        'Content-Type': 'application/json',
        'Accept': 'text/html, */*',
        'Content-MD5': md5(payload).hexdigest()
    }


def http_emitter(message, log, agentConfig):
    """Send payload
    """

    log.debug('http_emitter: attempting postback to ' + agentConfig['forwarder_url'])

    # Post back the data
    partial_payload = []
    for measurement in message:
        if not isinstance(measurement, Measurement):
            log.error('Data was not in the form of a monagent.common.metrics.Measurement')
            continue
        # Measurements need their __dict__ encoded to avoid being expressed as a tuple
        partial_payload.append(measurement.__dict__)

    payload = json.dumps(partial_payload)
    url = "%s/intake" % agentConfig['forwarder_url']
    headers = post_headers(agentConfig, payload)

    try:
        request = urllib2.Request(url, payload, headers)
        response = urllib2.urlopen(request)
        try:
            log.debug('http_emitter: postback response: ' + str(response.read()))
        finally:
            response.close()
    except urllib2.HTTPError, e:
        if e.code == 202:
            log.debug("http payload accepted")
        else:
            raise
