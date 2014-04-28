import zlib
from util import json, md5, get_os
import urllib2

def post_headers(agentConfig, payload):
    return {
        'User-Agent': 'Datadog Agent/%s' % agentConfig['version'],
        'Content-Type': 'application/json',
        'Content-Encoding': 'deflate',
        'Accept': 'text/html, */*',
        'Content-MD5': md5(payload).hexdigest()
    }

def http_emitter(message, log, agentConfig):
    "Send payload"

    log.debug('http_emitter: attempting postback to ' + agentConfig['forwarder_url'])

    # Post back the data
    payload = json.dumps(message)
    zipped = zlib.compress(payload)

    log.debug("payload_size=%d, compressed_size=%d, compression_ratio=%.3f" % (len(payload), len(zipped), float(len(payload))/float(len(zipped))))

    url = "%s/intake" % agentConfig['forwarder_url']
    headers = post_headers(agentConfig, zipped)

    try:
        request = urllib2.Request(url, zipped, headers)
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
