from hashlib import md5
import json
import urllib2


def post_headers(agentConfig, payload):
    return {
        'User-Agent': 'Datadog Agent/%s' % agentConfig['version'],
        'Content-Type': 'application/json',
        'Accept': 'text/html, */*',
        'Content-MD5': md5(payload).hexdigest()
    }



def http_emitter(message, log, agentConfig):
    "Send payload"

    log.debug('http_emitter: attempting postback to ' + agentConfig['forwarder_url'])

    # Post back the data
    payload = json.dumps(message)

    url = "%s/intake" % agentConfig['forwarder_url']
    headers = post_headers(agentConfig, payload)

    try:
        request = urllib2.Request(url, payload, headers)
        # Do the request, log any errors
        opener = urllib2.build_opener()
        if opener is not None:
            urllib2.install_opener(opener)
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
