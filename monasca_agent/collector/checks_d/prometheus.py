# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
import math
import requests
import six

from prometheus_client.parser import text_string_to_metric_families

import monasca_agent.collector.checks as checks
import monasca_agent.collector.checks.utils as utils

KUBERNETES_LABELS = ['app']


class Prometheus(checks.AgentCheck):
    """Scrapes metrics from Prometheus endpoints
    Can be configured three ways:
        1. Autodetect endpoints by pod annotations
        2. Autodetect endpoints by services
        3. Manually configure each prometheus endpoints to scrape

    We autodetect based on the annotations assigned to pods/services.

    We look for the following entries:
    'prometheus.io/scrape': Only scrape pods that have a value of 'true'
    'prometheus.io/path': If the metrics path is not '/metrics' override this.
    'prometheus.io/port': Scrape the pod on the indicated port instead of the default of '9102'.
    """

    def __init__(self, name, init_config, agent_config, instances=None):
        super(Prometheus, self).__init__(name, init_config, agent_config, instances)
        self.connection_timeout = init_config.get("timeout", 3)
        self.auto_detect_endpoints = init_config.get("auto_detect_endpoints", False)
        if self.auto_detect_endpoints:
            self.kubernetes_connector = None
            self.detect_method = init_config.get("detect_method", "pod").lower()
            self.kubelet_url = None
            if instances is not None and len(instances) > 1:
                raise Exception('Prometheus Client only supports one configured instance if auto detection is set')
            if self.detect_method not in ['pod', 'service']:
                raise Exception('Invalid detect method {}. Must be either pod or service')

    def check(self, instance):
        dimensions = self._set_dimensions(None, instance)
        del dimensions['hostname']
        if not self.auto_detect_endpoints:
            metric_endpoint = instance.get("metric_endpoint", None)
            if not metric_endpoint:
                self.log.error("metric_endpoint must be defined for each instance")
                return
            endpoint_dimensions = instance.get("default_dimensions", {})
            endpoint_dimensions.update(dimensions)
            self.report_endpoint_metrics(metric_endpoint, endpoint_dimensions)
        else:
            self.kubernetes_labels = instance.get('kubernetes_labels', KUBERNETES_LABELS)
            if not self.kubernetes_connector:
                self.kubernetes_connector = utils.KubernetesConnector(self.connection_timeout)
            if self.detect_method == "pod":
                if not self.kubelet_url:
                    try:
                        host = self.kubernetes_connector.get_agent_pod_host()
                        self.kubelet_url = "http://{}:10255/pods".format(host)
                    except Exception as e:
                        self.log.error("Could not obtain current host from Kubernetes API {}. "
                                       "Skipping check".format(e))
                        return
                metric_endpoints = self._get_metric_endpoints_by_pod(dimensions)
            # Detect by service
            else:
                metric_endpoints = self._get_metric_endpoints_by_service(dimensions)
            for metric_endpoint, endpoint_dimensions in six.iteritems(metric_endpoints):
                endpoint_dimensions.update(dimensions)
                self.report_endpoint_metrics(metric_endpoint, endpoint_dimensions)

    def _get_metric_endpoints_by_pod(self, dimensions):
        scrape_endpoints = {}
        # Grab running pods from local Kubelet
        try:
            pods = requests.get(self.kubelet_url, timeout=self.connection_timeout).json()
        except Exception as e:
            exception_message = "Could not get pods from local kubelet with error - {}".format(e)
            self.log.exception(exception_message)
            raise Exception(exception_message)

        # Iterate through each pod and check if it contains a scrape endpoint
        for pod in pods['items']:
            try:
                pod_metadata = pod['metadata']
                pod_spec = pod['spec']
                pod_status = pod['status']
                if "annotations" not in pod_metadata or not ('containers' in pod_spec and 'podIP' in pod_status):
                    # No annotations, containers, or endpoints skipping pod
                    continue

                # Check pod annotations if we should scrape pod
                pod_annotations = pod_metadata['annotations']
                prometheus_scrape = pod_annotations.get("prometheus.io/scrape", "false").lower()
                if prometheus_scrape != "true":
                    continue
                pod_ports = []
                pod_containers = pod_spec['containers']
                for container in pod_containers:
                    if "ports" in container:
                        pod_ports += container['ports']
                pod_name = pod_metadata['name']
                endpoints = self._get_prometheus_endpoint(pod_annotations, pod_ports, pod_name)
                if not endpoints:
                    continue

                # Add pod endpoint to scrape endpoints
                pod_ip = pod_status['podIP']
                # Loop through list of ports and build list of endpoints

                pod_dimensions = dimensions.copy()
                pod_dimensions.update(utils.get_pod_dimensions(
                    self.kubernetes_connector, pod['metadata'],
                    self.kubernetes_labels))
                for endpoint in endpoints:
                    scrape_endpoint = "http://{}:{}".format(pod_ip, endpoint)
                    scrape_endpoints[scrape_endpoint] = pod_dimensions
                    self.log.info("Detected pod endpoint - {} with metadata "
                                  "of {}".format(scrape_endpoint,
                                                 pod_dimensions))
            except Exception as e:
                self.log.warn("Error parsing {} to detect for scraping - {}".format(pod, e))
                continue

        return scrape_endpoints

    def _get_metric_endpoints_by_service(self, dimensions):
        scrape_endpoints = {}
        # Grab services from Kubernetes API
        try:
            services = self.kubernetes_connector.get_request("/api/v1/services")
        except Exception as e:
            exception_message = "Could not get services from Kubernetes API with error - {}".format(e)
            self.log.exception(exception_message)
            raise Exception(exception_message)

        # Iterate through each service and check if it is a scape endpoint
        for service in services['items']:
            service_metadata = service['metadata']
            service_spec = service['spec']
            if "annotations" not in service_metadata or "ports" not in service_spec:
                # No annotations or pods skipping service
                continue

            # Check service annotations if we should scrape service
            service_annotations = service_metadata['annotations']
            prometheus_scrape = service_annotations.get("prometheus.io/scrape", "false").lower()
            if prometheus_scrape != "true":
                continue
            service_name = service_metadata['name']
            service_ports = service_spec['ports']
            endpoints = self._get_prometheus_endpoint(service_annotations,
                                                      service_ports,
                                                      service_name)
            if not endpoints:
                continue

            # Add service endpoint to scrape endpoints
            cluster_ip = service_spec['clusterIP']
            service_dimensions = dimensions.copy()
            service_dimensions.update(
                self._get_service_dimensions(service_metadata))
            for endpoint in endpoints:
                scrape_endpoint = "http://{}:{}".format(cluster_ip, endpoint)
                scrape_endpoints[scrape_endpoint] = service_dimensions
                self.log.info("Detected service endpoint - {} with metadata "
                              "of {}".format(scrape_endpoint,
                                             service_dimensions))
        return scrape_endpoints

    def _get_service_dimensions(self, service_metadata):
        service_dimensions = {'service_name': service_metadata['name'],
                              'namespace': service_metadata['namespace']}
        if "labels" in service_metadata:
            service_labels = service_metadata['labels']
            for label in self.kubernetes_labels:
                if label in service_labels:
                    service_dimensions[label] = service_labels[label]
        return service_dimensions

    def _get_prometheus_endpoint(self, annotations, ports, name):
        """Analyzes annotations and ports to generate a scrape target"""
        pod_index = "containerPort" if self.detect_method == "pod" else "port"
        configured_ports = []
        if "prometheus.io/port" in annotations:
            configured_ports = annotations.get("prometheus.io/port").split(',')
            configured_ports = [int(i) for i in configured_ports]

        if self.detect_method == "pod" and not configured_ports:
            configured_ports = [9102]
        prometheus_endpoint = annotations.get("prometheus.io/path", "/metrics")

        endpoints = []
        for port in ports:
            for configured_port in configured_ports:
                if port[pod_index] == configured_port:
                    # Build up list of ports and prometheus endpoints to return
                    endpoints += "{}/{}".format(configured_port,
                                                prometheus_endpoint)

        if len(ports) == 1 and not endpoints:
            self.log.info("Could not find matching port using only port "
                          "configured")
            endpoints += "{}/{}".format(ports[pod_index], prometheus_endpoint)

        if not endpoints:
            self.log.error("Can not derive which port to use. Due to more "
                           "then one port configured and none of them "
                           "selected via configurations. {} {} skipped for "
                           "scraping".format(self.detect_method, name))
        return endpoints

    def _send_metrics(self, metric_families, dimensions):
        for metric_family in metric_families:
            for metric in metric_family.samples:
                metric_dimensions = dimensions.copy()
                metric_name = metric[0]
                metric_labels = metric[1]
                metric_value = float(metric[2])
                if math.isnan(metric_value):
                    self.log.debug('filtering out NaN value provided for metric %s{%s}', metric_name, metric_labels)
                    continue
                # remove empty string dimensions from prometheus labels
                for dim_key, dim_value in metric_labels.items():
                    if len(dim_value) > 0:
                        metric_dimensions[dim_key] = dim_value
                self.gauge(metric_name, metric_value, dimensions=metric_dimensions, hostname="SUPPRESS")

    def report_endpoint_metrics(self, metric_endpoint, endpoint_dimensions):
        # Hit metric endpoint
        try:
            result = requests.get(metric_endpoint, timeout=self.connection_timeout)
        except Exception as e:
            self.log.error("Could not get metrics from {} with error {}".format(metric_endpoint, e))
        else:
            result_content_type = result.headers['Content-Type']
            if "text/plain" in result_content_type:
                try:
                    metric_families = text_string_to_metric_families(result.text)
                    self._send_metrics(metric_families, endpoint_dimensions)
                except Exception as e:
                    self.log.error("Error parsing data from {} with error {}".format(metric_endpoint, e))
            else:
                self.log.error("Unsupported content type - {}".format(result_content_type))
