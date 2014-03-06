import zlib
import sys
import time
import requests
from monapi.monapi import MonAPI
from util import json, md5


def get_http_library(proxy_settings, use_forwarder):
    #There is a bug in the https proxy connection in urllib2 on python < 2.6.3
    if use_forwarder:
        # We are using the forwarder, so it's local trafic. We don't use the proxy
        import urllib2

    elif proxy_settings is None or int(sys.version_info[1]) >= 7\
        or (int(sys.version_info[1]) == 6 and int(sys.version_info[2]) >= 3):
        # Python version >= 2.6.3
        import urllib2

    else:
        # Python version < 2.6.3
        import urllib2proxy as urllib2
    return urllib2 

def post_headers(agentConfig, payload):
    return {
        'User-Agent': 'Monitoring Agent/%s' % agentConfig['version'],
        'Content-Type': 'application/json',
        'Content-Encoding': 'deflate',
        'Accept': 'text/html, */*',
        'Content-MD5': md5(payload).hexdigest()
    }

def http_emitter(message, logger, agentConfig):
    "Send payload"

    logger.debug('http_emitter: attempting postback to ' + agentConfig['dd_url'])

    # Post back the data
    payload = json.dumps(message)
    zipped = zlib.compress(payload)

    logger.debug("payload_size=%d, compression_ration=%d" %(len(zipped), len(payload)/len(zipped)))

    # Build the request handler
    apiKey = message.get('apiKey', None)
    if not apiKey:
        raise Exception("The http emitter requires an api key")

    url = "%s/intake?api_key=%s" % (agentConfig['dd_url'], apiKey)
    headers = post_headers(agentConfig, zipped)

    proxy_settings = agentConfig.get('proxy_settings', None)
    urllib2 = get_http_library(proxy_settings, agentConfig['use_forwarder'])

    try:
        request = urllib2.Request(url, zipped, headers)
        # Do the request, logger any errors
        opener = get_opener(logger, proxy_settings, agentConfig['use_forwarder'], urllib2)
        if opener is not None:
            urllib2.install_opener(opener)
        response = urllib2.urlopen(request)
        try:
            logger.debug('http_emitter: postback response: ' + str(response.read()))
        finally:
            response.close()
    except urllib2.HTTPError, e:
        if e.code == 202:
            logger.debug("http payload accepted")
        else:
            raise

def get_metric(message):
    blacklist = ["collection_timestamp"]
    timestamp = get_timestamp(message)
    for key in message:
        if key not in blacklist:
            value = message[key]
            if isinstance(value, int) or isinstance(value, float):
                metric = {"namespace": "collector", "dimensions": {"name": key}, "timestamp": timestamp, "value": value}
                yield metric
                #str_metric = json.dumps(metric)
                #yield str_metric

def get_timestamp(message):
    if "collection_timestamp" in message:
        timestamp = message["collection_timestamp"]
    else:
        timestamp = time.gmtime()
    return timestamp

def mon_api_http_emitter(message, logger, agentConfig):
    logger.debug('mon_api_http_emitter: attempting postback to ' + agentConfig['dd_url'])
    mon_api_url = agentConfig['mon_api_url']
    project_id = agentConfig['mon_api_project_id']
    user_id = agentConfig['mon_api_username']
    password = agentConfig['mon_api_password']
    keystone_url = agentConfig['keystone_url']
    api = MonAPI(mon_api_url, keystone_url, project_id, user_id, password)

    for body in get_metric(message):
        try:
            api.create_or_update_metric(body)
            #logger.debug('mon_api_http_emitter: postback response: ' + str(response.read()))
        except Exception as ex:
            logger.debug("")

def get_opener(logger, proxy_settings, use_forwarder, urllib2):
    if use_forwarder:
        # We are using the forwarder, so it's local trafic. We don't use the proxy
        return None

    if proxy_settings is None:
        # urllib2 will figure out how to connect automatically        
        return None

    proxy_url = '%s:%s' % (proxy_settings['host'], proxy_settings['port'])
    if proxy_settings.get('user') is not None:
        proxy_auth = proxy_settings['user']
        if proxy_settings.get('password') is not None:
            proxy_auth = '%s:%s' % (proxy_auth, proxy_settings['password'])
        proxy_url = '%s@%s' % (proxy_auth, proxy_url)
        
    proxy = {'https': proxy_url}
    logger.info("Using proxy settings %s" % proxy)
    proxy_handler = urllib2.ProxyHandler(proxy)
    opener = urllib2.build_opener(proxy_handler)
    return opener
