# (C) Copyright 2017-2018 Hewlett Packard Enterprise Development LP
import math
import requests
import six
import time
import yaml

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

    Additional settings for prometheus endpoints
    'monasca.io/usek8slabels': Attach kubernetes labels of the pod that is being scraped. Default to 'true'
    'monasca.io/whitelist': Yaml list of metric names to whitelist against on detected endpoint
    'monasca.io/report_pod_label_owner': If the metrics that are scraped contain pod as a label key we will attempt to get the
    pod owner and attach that to the metric as another dimension. Very useful for other scraping from other solutions
    that monitor k8s (Ex. kube-state-metrics). Default to 'false'
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
            self.k8s_pod_cache = None
            self.cache_start_time = None

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
            # Check if we need to clear pod cache so it does not build up over time
            if self.k8s_pod_cache is not None:
                if not self.cache_start_time:
                    self.cache_start_time = time.time()
                else:
                    current_time = time.time()
                    if (current_time - self.cache_start_time) > 86400:
                        self.cache_start_time = current_time
                        self.k8s_pod_cache = {}
                        self.initialize_pod_cache()
            if self.detect_method == "pod":
                if not self.kubelet_url:
                    try:
                        host = self.kubernetes_connector.get_agent_pod_host()
                        self.kubelet_url = "http://{}:10255/pods".format(host)
                    except Exception as e:
                        self.log.error("Could not obtain current host from Kubernetes API {}. "
                                       "Skipping check".format(e))
                        return
                prometheus_endpoints = self._get_metric_endpoints_by_pod(dimensions)
            # Detect by service
            else:
                prometheus_endpoints = self._get_metric_endpoints_by_service(dimensions)
            for prometheus_endpoint in prometheus_endpoints:
                self.report_endpoint_metrics(prometheus_endpoint.scrape_endpoint, prometheus_endpoint.dimensions,
                                             prometheus_endpoint.whitelist, prometheus_endpoint.metric_types,
                                             prometheus_endpoint.report_pod_label_owner)

    def _get_metric_endpoints_by_pod(self, dimensions):
        prometheus_endpoints = []
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
                try:
                    use_k8s_labels, whitelist, metric_types, report_pod_label_owner = \
                        self._get_monasca_settings(pod_name, pod_annotations)
                except Exception as e:
                    error_message = "Error parsing monasca annotations on endpoints {} with error - {}. " \
                                    "Skipping scraping metrics".format(endpoints, e)
                    self.log.error(error_message)
                    continue
                # set global_pod_cache
                if report_pod_label_owner and self.k8s_pod_cache is None:
                    self.k8s_pod_cache = {}
                    self.initialize_pod_cache()
                if use_k8s_labels:
                    pod_dimensions.update(utils.get_pod_dimensions(
                        self.kubernetes_connector, pod['metadata'],
                        self.kubernetes_labels))
                for endpoint in endpoints:
                    scrape_endpoint = "http://{}:{}".format(pod_ip, endpoint)
                    prometheus_endpoint = PrometheusEndpoint(scrape_endpoint, pod_dimensions, whitelist, metric_types,
                                                             report_pod_label_owner)
                    prometheus_endpoints.append(prometheus_endpoint)
                    self.log.info("Detected pod endpoint - {} with metadata "
                                  "of {}".format(scrape_endpoint,
                                                 pod_dimensions))
            except Exception as e:
                self.log.warn("Error parsing {} to detect for scraping - {}".format(pod, e))
                continue

        return prometheus_endpoints

    def _get_metric_endpoints_by_service(self, dimensions):
        prometheus_endpoints = []
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
            try:
                use_k8s_labels, whitelist, metric_types, report_pod_label_owner = \
                    self._get_monasca_settings(service_name, service_annotations)
            except Exception as e:
                error_message = "Error parsing monasca annotations on endpoints {} with error - {}. " \
                                "Skipping scraping metrics".format(endpoints, e)
                self.log.error(error_message)
                continue
                # set global_pod_cache
            if report_pod_label_owner and self.k8s_pod_cache is None:
                self.k8s_pod_cache = {}
                self.initialize_pod_cache()
            if use_k8s_labels:
                service_dimensions.update(
                    self._get_service_dimensions(service_metadata))
            for endpoint in endpoints:
                scrape_endpoint = "http://{}:{}".format(cluster_ip, endpoint)
                prometheus_endpoint = PrometheusEndpoint(scrape_endpoint, service_dimensions, whitelist, metric_types,
                                                         report_pod_label_owner)
                prometheus_endpoints.append(prometheus_endpoint)
                self.log.info("Detected service endpoint - {} with metadata "
                              "of {}".format(scrape_endpoint,
                                             service_dimensions))
        return prometheus_endpoints

    def _get_monasca_settings(self, resource_name, annotations):
        use_k8s_labels = annotations.get("monasca.io/usek8slabels", "true").lower() == "true"
        whitelist = None
        if "monasca.io/whitelist" in annotations:
            whitelist = yaml.safe_load(annotations["monasca.io/whitelist"])
        metric_types = None
        if "monasca.io/metric_types" in annotations:
            metric_types = yaml.safe_load(annotations["monasca.io/metric_types"])
            for typ in metric_types:
                if metric_types[typ] not in ['rate', 'counter']:
                    self.log.warn("Ignoring unknown metric type '{}' configured for '{}' on endpoint '{}'".format(
                        typ, metric_types[typ], resource_name))
                    del metric_types[typ]
        report_pod_label_owner_annotation = annotations.get("monasca.io/report_pod_label_owner", "false").lower()
        report_pod_label_owner = True if report_pod_label_owner_annotation == "true" else False
        return use_k8s_labels, whitelist, metric_types, report_pod_label_owner

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
        prometheus_endpoint = prometheus_endpoint.lstrip('/')

        endpoints = []
        for port in ports:
            for configured_port in configured_ports:
                if port[pod_index] == configured_port:
                    # Build up list of ports and prometheus endpoints to return
                    endpoints.append("{}/{}".format(configured_port,
                                                    prometheus_endpoint))

        if len(ports) == 1 and not endpoints:
            self.log.info("Could not find matching port using only port "
                          "configured")
            endpoints.append("{}/{}".format(ports[0][pod_index], prometheus_endpoint))

        if not endpoints:
            self.log.error("Can not derive which port to use. Due to either "
                           "no port being exposed or more than one port "
                           "configured and none of them selected via "
                           "configurations. "
                           "{} {} skipped for scraping".format(self.detect_method, name))
        self.log.debug("Found prometheus endpoints '{}'".format(endpoints))
        return endpoints

    def _send_metrics(self, metric_families, dimensions, endpoint_whitelist, endpoint_metric_types,
                      report_pod_label_owner):
        for metric_family in metric_families:
            for metric in metric_family.samples:
                metric_dimensions = dimensions.copy()
                metric_name = metric[0]
                metric_labels = metric[1]
                metric_value = float(metric[2])
                if math.isnan(metric_value):
                    self.log.debug('filtering out NaN value provided for metric %s{%s}', metric_name, metric_labels)
                    continue
                if endpoint_whitelist is not None and metric_name not in endpoint_whitelist:
                    continue
                # remove empty string dimensions from prometheus labels
                for dim_key, dim_value in metric_labels.items():
                    if len(dim_value) > 0:
                        metric_dimensions[dim_key] = dim_value

                metric_func = self.gauge
                if endpoint_metric_types and metric_name in endpoint_metric_types:
                    typ = endpoint_metric_types[metric_name]
                    if typ == "rate":
                        metric_func = self.rate
                        metric_name += "_rate"
                    elif typ == "counter":
                        metric_func = self.increment
                        metric_name += "_counter"
                if report_pod_label_owner:
                    if "pod" in metric_dimensions and "namespace" in metric_dimensions:
                        pod_name = metric_dimensions["pod"]
                        if pod_name in self.k8s_pod_cache:
                            pod_owner, pod_owner_name = self.k8s_pod_cache[pod_name]
                            metric_dimensions[pod_owner] = pod_owner_name
                            metric_dimensions["owner_type"] = pod_owner
                        else:
                            pod_owner_pair = self.get_pod_owner(pod_name, metric_dimensions['namespace'])
                            if pod_owner_pair:
                                pod_owner = pod_owner_pair[0]
                                pod_owner_name = pod_owner_pair[1]
                                metric_dimensions[pod_owner] = pod_owner_name
                                metric_dimensions["owner_type"] = pod_owner
                                self.k8s_pod_cache[pod_name] = pod_owner, pod_owner_name
                metric_func(metric_name, metric_value, dimensions=metric_dimensions, hostname="SUPPRESS")

    def report_endpoint_metrics(self, metric_endpoint, endpoint_dimensions, endpoint_whitelist=None,
                                endpoint_metric_types=None, report_pod_label_owner=False):
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
                    self._send_metrics(metric_families, endpoint_dimensions, endpoint_whitelist, endpoint_metric_types,
                                       report_pod_label_owner)
                except Exception as e:
                    self.log.error("Error parsing data from {} with error {}".format(metric_endpoint, e))
            else:
                self.log.error("Unsupported content type - {}".format(result_content_type))

    def get_pod_owner(self, pod_name, namespace):
        try:
            pod = self.kubernetes_connector.get_request("/api/v1/namespaces/{}/pods/{}".format(namespace, pod_name))
            pod_metadata = pod['metadata']
            pod_owner, pod_owner_name = utils.get_pod_owner(self.kubernetes_connector, pod_metadata)
            if not pod_owner:
                self.log.info("Could not get pod owner for pod {}".format(pod_name))
                return None
            return pod_owner, pod_owner_name
        except Exception as e:
            self.log.info("Could not get pod {} from Kubernetes API with error - {}".format(pod_name, e))
            return None

    def initialize_pod_cache(self):
        self.k8s_pod_cache = {}
        try:
            pods = self.kubernetes_connector.get_request("/api/v1/pods")
        except Exception as e:
            exception_message = "Could not get pods from Kubernetes API with error - {}".format(e)
            self.log.exception(exception_message)
            raise Exception(exception_message)
        for pod in pods['items']:
            pod_metadata = pod['metadata']
            pod_name = pod_metadata['name']
            try:
                pod_owner, pod_owner_name = utils.get_pod_owner(self.kubernetes_connector, pod_metadata)
            except Exception as e:
                self.log.info("Error attempting to get pod {} owner with error {}".format(pod_name, e))
                continue
            if not pod_owner:
                self.log.info("Could not get pod owner for pod {}".format(pod_name))
                continue
            self.k8s_pod_cache[pod_name] = (pod_owner, pod_owner_name)


# Class to hold prometheus endpoint metadata
class PrometheusEndpoint(object):
    def __init__(self, scrape_endpoint, dimensions, whitelist, metric_types, report_pod_label_owner):
        self.scrape_endpoint = scrape_endpoint
        self.dimensions = dimensions
        self.whitelist = whitelist
        self.metric_types = metric_types
        self.report_pod_label_owner = report_pod_label_owner
