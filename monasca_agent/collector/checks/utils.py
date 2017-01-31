# (C) Copyright 2015,2017 Hewlett Packard Enterprise Development LP

import base64
import logging
import math
import os
import requests

from monasca_agent.common import exceptions

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20


def add_basic_auth(request, username, password):
    """A helper to add basic authentication to a urllib2 request.

    We do this across a variety of checks so it's good to have this in one place.
    """
    auth_str = base64.encodestring('%s:%s' % (username, password)).strip()
    request.add_header('Authorization', 'Basic %s' % auth_str)
    return request


def get_keystone_client(config):
    import keystoneclient.v2_0.client as kc
    kwargs = {
        'username': config.get('admin_user'),
        'project_name': config.get('admin_tenant_name'),
        'password': config.get('admin_password'),
        'auth_url': config.get('identity_uri'),
        'endpoint_type': 'internalURL',
        'region_name': config.get('region_name'),
    }

    return kc.Client(**kwargs)


def get_tenant_name(tenants, tenant_id):
    tenant_name = None
    for tenant in tenants:
        if tenant.id == tenant_id:
            tenant_name = tenant.name
            break
    return tenant_name


def get_tenant_list(config, log):
    tenants = []
    try:
        log.debug("Retrieving Keystone tenant list")
        keystone = get_keystone_client(config)
        tenants = keystone.tenants.list()
    except Exception as e:
        msg = "Unable to get tenant list from keystone: {0}"
        log.error(msg.format(e))

    return tenants


def convert_memory_string_to_bytes(memory_string):
    """Conversion from memory represented in string format to bytes"""
    if "m" in memory_string:
        memory = float(memory_string.split('m')[0])
        return memory / 1000
    elif "K" in memory_string:
        memory = float(memory_string.split('K')[0])
        return _compute_memory_bytes(memory_string, memory, 1)
    elif "M" in memory_string:
        memory = float(memory_string.split('M')[0])
        return _compute_memory_bytes(memory_string, memory, 2)
    elif "G" in memory_string:
        memory = float(memory_string.split('G')[0])
        return _compute_memory_bytes(memory_string, memory, 3)
    elif "T" in memory_string:
        memory = float(memory_string.split('T')[0])
        return _compute_memory_bytes(memory_string, memory, 4)
    else:
        return float(memory_string)


def _compute_memory_bytes(memory_string, memory, power):
    if "i" in memory_string:
        return memory * math.pow(1024, power)
    return memory * math.pow(1000, power)


class KubernetesConnector(object):
    """Class for connecting to Kubernetes API from within a container running
    in a Kubernetes environment
    """
    CACERT_PATH = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
    TOKEN_PATH = '/var/run/secrets/kubernetes.io/serviceaccount/token'

    def __init__(self, connection_timeout):
        self.api_url = None
        self.api_verify = None
        self.api_request_header = None
        if connection_timeout is None:
            self.connection_timeout = DEFAULT_TIMEOUT
        else:
            self.connection_timeout = connection_timeout
        self._set_kubernetes_api_connection_info()
        self._set_kubernetes_service_account_info()

    def _set_kubernetes_api_connection_info(self):
        """Set kubernetes API string from default container environment
        variables
        """
        api_host = os.environ.get('KUBERNETES_SERVICE_HOST', "kubernetes")
        api_port = os.environ.get('KUBERNETES_SERVICE_PORT', "443")
        self.api_url = "https://{}:{}".format(api_host, api_port)

    def _set_kubernetes_service_account_info(self):
        """Set cert and token info to included on requests to the API"""
        try:
            with open(self.TOKEN_PATH) as token_file:
                token = token_file.read()
        except Exception as e:
            log.error("Unable to read token - {}. Defaulting to using no token".format(e))
            token = None
        self.api_request_header = {'Authorization': 'Bearer {}'.format(token)} if token else None
        self.api_verify = self.CACERT_PATH if os.path.exists(self.CACERT_PATH) else False

    def get_agent_pod_host(self, return_host_name=False):
        """Obtain host the agent is running on in Kubernetes.
        Used when trying to connect to services running on the node (Kubelet, cAdvisor)
        """
        # Get pod name and namespace from environment variables
        pod_name = os.environ.get("AGENT_POD_NAME")
        pod_namespace = os.environ.get("AGENT_POD_NAMESPACE")
        if not pod_name:
            raise exceptions.MissingEnvironmentVariables(
                "pod_name is not set as environment variables cannot derive"
                " host from Kubernetes API")
        if not pod_namespace:
            raise exceptions.MissingEnvironmentVariables(
                "pod_namespace is not set as environment variables cannot "
                "derive host from Kubernetes API")
        pod_url = "/api/v1/namespaces/{}/pods/{}".format(pod_namespace, pod_name)
        try:
            agent_pod = self.get_request(pod_url)
        except Exception as e:
            exception_message = "Could not get agent pod from Kubernetes API" \
                                " to get host IP with error - {}".format(e)
            log.exception(exception_message)
            raise exceptions.KubernetesAPIConnectionError(exception_message)
        if not return_host_name:
            return agent_pod['status']['hostIP']
        else:
            return agent_pod['spec']['nodeName']

    def get_request(self, request_endpoint, as_json=True, retried=False):
        """Sends request to Kubernetes API with given endpoint.
        Will retry the request once, with updated token/cert, if unauthorized.
        """
        request_url = "{}/{}".format(self.api_url, request_endpoint)
        result = requests.get(request_url,
                              timeout=self.connection_timeout,
                              headers=self.api_request_header,
                              verify=self.api_verify)
        if result.status_code >= 300:
            if result.status_code == 401 and not retried:
                log.info("Could not authenticate with Kubernetes API at the"
                         " first time. Rereading in cert and token.")
                self._set_kubernetes_service_account_info()
                return self.get_request(request_endpoint, as_json=as_json,
                                        retried=True)
            exception_message = "Could not obtain data from {} with the " \
                                "given status code {} and return text {}".\
                format(request_url, result.status_code, result.text)
            raise exceptions.KubernetesAPIConnectionError(exception_message)
        return result.json() if as_json else result
