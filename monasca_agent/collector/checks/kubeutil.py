# stdlib
import logging
import socket
import struct
from urlparse import urljoin
import requests


def retrieve_json(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.json()


# project

DEFAULT_METHOD = 'http'
METRICS_PATH = '/api/v1.3/subcontainers/'
CONTAINERS_PATH = '/api/v1.3/containers/'
DEFAULT_CADVISOR_PORT = 4194
DEFAULT_KUBELET_PORT = 10255
DEFAULT_MASTER_PORT = 8080

log = logging.getLogger('collector')
_kube_settings = {}


def get_kube_settings():
    global _kube_settings
    return _kube_settings


def set_kube_settings(instance):
    global _kube_settings

    host = instance.get("host") or _get_node_name()
    cadvisor_port = instance.get('port', DEFAULT_CADVISOR_PORT)
    method = instance.get('method', DEFAULT_METHOD)
    metrics_url = urljoin('%s://%s:%d' % (method, host, cadvisor_port), METRICS_PATH)
    kubelet_port = instance.get('kubelet_port', DEFAULT_KUBELET_PORT)
    master_port = instance.get('master_port', DEFAULT_MASTER_PORT)
    master_host = instance.get('master_host', host)

    _kube_settings = {
        "host": host,
        "method": method,
        "metrics_url": metrics_url,
        "cadvisor_port": cadvisor_port,
        "labels_url": '%s://%s:%d/pods' % (method, host, kubelet_port),
        "master_url_nodes": '%s://%s:%d/api/v1/nodes' % (method, master_host, master_port),
        "kube_health_url": '%s://%s:%d/healthz' % (method, host, kubelet_port)
    }

    return _kube_settings


def get_kube_labels():
    global _kube_settings
    pods = retrieve_json(_kube_settings["labels_url"])
    kube_labels = {}
    for pod in pods["items"]:
        metadata = pod.get("metadata", {})
        name = metadata.get("name")
        namespace = metadata.get("namespace")
        labels = metadata.get("labels")
        if name and labels and namespace:
            key = "%s/%s" % (namespace, name)
            kube_labels[key] = labels

    return kube_labels


def _get_node_name():
    try:
        # TODO: use K8S API to get hostname of port (we should have some simple wrapper for the API here)
        """
        KUBE_TOKEN=$(</var/run/secrets/kubernetes.io/serviceaccount/token)
        export KUBE_NODE=`unset https_proxy; unset http_proxy; unset all_proxy; curl -sSk -H "Authorization: Bearer $KUBE_TOKEN" \
        https://$KUBERNETES_SERVICE_HOST:$KUBERNETES_PORT_443_TCP_PORT/api/v1/namespaces/$KUBE_NAMESPACE/pods/$HOSTNAME| grep  "nodeName"| awk -F: '{ print $2}'|sed 's/\"//g'`
        """
        raise IOError('_get_node_name() not implemented')

    except IOError as e:
        log.error('Unable to open /proc/net/route: %s', e)

    return None
