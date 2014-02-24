import zlib
import sys
from pprint import pformat as pp
from util import json, md5, get_os
from config import get_ssl_certificate
import time
import requests

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
        'User-Agent': 'Datadog Agent/%s' % agentConfig['version'],
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

class Region(object):
    domains = {
        'rndd': 'rndd.aw1.hpcloud.net',
        'stb': 'systest.hpcloud.net',
        'uswest': 'uswest.hpcloud.net',
        'useast': 'useast.hpcloud.net'
    }
    keystones = {
        'rndd': 'keystone.rndd.aw1.hpcloud.net',
        'stb': 'keystone.systest.hpcloud.net',
        'uswest': 'region-a.geo-1.identity.hpcloudsvc.com',
        'useast': 'region-b.geo-1.identity.hpcloudsvc.com'
    }

    def __init__(self, region_name):
        self.domain = self.domains.get(region_name, None)
        if not self.domain:
            raise ValueError("Unknown region: %s" % region_name)
        self.keystone = self.keystones[region_name]

class Keystone(object):
    endpoint_template = "https://%s:35357/v3/auth/tokens"

    password_auth = {
        "auth": {
            "identity": {
                "methods": [
                    "password"
                ],
                "password": {
                    "user": {
                    }
                }
            },
            "scope": {
                "project": {
                }
            }
        }
    }

    access_token_auth = {
        "auth": {
            "identity": {
                "methods": [
                    "accessKey"
                ],
                "accessKey": {
                    "accessKey": {},
                    "secretKey": {},
                }
            }
        }
    }

    rescope_access_token = {
        "auth": {
            "identity": {
                "methods": [
                    "token"
                ],
                "token": {
                    "id": {}
                }
            },
            "scope": {
                "project": {
                    "id": {}
                }
            }
        }
    }

    def __init__(self, region):
        if not isinstance(region, Region):
            region = Region(region)
        self.endpoint = self.endpoint_template % region.keystone

    def get_token_password_auth(self, user_id, password, project_id):
        self.password_auth['auth']['identity']['password']['user']['id'] = user_id
        self.password_auth['auth']['identity']['password']['user']['password'] = password
        self.password_auth['auth']['scope']['project']['id'] = project_id
        data = json.dumps(self.password_auth)
        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.endpoint, data=data, headers=headers)
        response.raise_for_status()
        return response.headers['X-Subject-Token']

    def get_token_access_key_auth(self, project_id, access_key, secret_key):
        self.access_token_auth['auth']['identity']['accessKey']['accessKey'] = access_key
        self.access_token_auth['auth']['identity']['accessKey']['secretKey'] = secret_key
        data = json.dumps(self.access_token_auth)
        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.endpoint, data=data, headers=headers)
        response.raise_for_status()
        first_token = response.headers['X-Subject-Token']
        self.rescope_access_token['auth']['scope']['project']['id'] = project_id
        self.rescope_access_token['auth']['identity']['token']['id'] = first_token
        data = json.dumps(self.rescope_access_token)
        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.endpoint, data=data, headers=headers)
        response.raise_for_status()
        return response.headers['X-Subject-Token']

class API(object):
    endpoint_template = 'https://region-a.geo-1.monitoring.hpcloudsvc.com/v1.1/metrics'

    def __init__(self, region_name, project_id, user_id, password):
        """
        Initialize SOM api connection.
        :param region_name: 'uswest' or 'useast'
        """
        self.region = Region(region_name)
        #self.project_id = project_id
        self.keystone = Keystone(self.region)
        self.token = self.keystone.get_token_password_auth(user_id, password, project_id)
        print self.token
        #self.token = self.keystone.get_token_access_key_auth(project_id, access_key, secret_key)
        #self.endpoint = self.endpoint_template % (self.region.domain)
        self.endpoint = self.endpoint_template
        self.headers = {'content-type': 'application/json',
                        'X-Auth-Token': self.token}

    def create_or_update_metric(self, payload):
        url = self.endpoint
        data = json.dumps(payload)
        response = requests.post(url, data=data, headers=self.headers, verify=False)
        response.raise_for_status()
        return

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
    for key in message:
        if key == "collection_timestamp":
            timestamp = message[key]
            return timestamp
    return time.gmtime()

def maas_http_emitter(message, logger, agentConfig):
    logger.debug('maas_http_emitter: attempting postback to ' + agentConfig['dd_url'])
    region = agentConfig['maas_region']
    project_id = agentConfig['maas_project_id']
    user_id = agentConfig['maas_username']
    password = agentConfig['maas_password']
    api = API(region, project_id, user_id, password)

    for body in get_metric(message):
        try:
            api.create_or_update_metric(body)
            #logger.debug('maas_http_emitter: postback response: ' + str(response.read()))
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
