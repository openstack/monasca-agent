# (C) Copyright 2017,2018 Hewlett Packard Enterprise Development LP
import logging
import requests

from monasca_agent.collector import checks
from monasca_agent.collector.checks import utils
from monasca_agent.common.util import rollup_dictionaries

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5
DEFAULT_KUBELET_PORT = "10255"
DEFAULT_CADVISOR_PORT = "4194"
CADVISOR_METRIC_URL = "/api/v2.0/stats?type=docker&recursive=true&count=1"
CADVISOR_SPEC_URL = "/api/v2.0/spec?type=docker&recursive=true"
POD_PHASE = {"Succeeded": 0,
             "Running": 1,
             "Pending": 2,
             "Failed": 3,
             "Unknown": 4}
REPORT_CONTAINER_METRICS = False
CADVISOR_METRICS = {
    "cpu_metrics": {
        "system": "cpu.system_time",
        "total": "cpu.total_time",
        "user": "cpu.user_time"
    },
    "memory_metrics": {
        "rss": "mem.rss_bytes",
        "swap": "mem.swap_bytes",
        "cache": "mem.cache_bytes",
        "usage": "mem.used_bytes",
        "failcnt": "mem.fail_count",
        "working_set": "mem.working_set_bytes"
    },
    "filesystem_metrics": {
        "capacity": "fs.total_bytes",
        "usage": "fs.usage_bytes",
        "writes_completed": "fs.writes",
        "reads_completes": "fs.reads",
        "io_in_progress": "fs.io_current"
    },
    "network_metrics": {
        "rx_bytes": "net.in_bytes",
        "tx_bytes": "net.out_bytes",
        "rx_packets": "net.in_packets",
        "tx_packets": "net.out_packets",
        "rx_dropped": "net.in_dropped_packets",
        "tx_dropped": "net.out_dropped_packets",
        "rx_errors": "net.in_errors",
        "tx_errors": "net.out_errors",
    },
    "diskio_metrics": {
        "Read": "io.read_bytes",
        "Write": "io.write_bytes"
    }
}

# format: (cadvisor metric name, [metric types], [metric units])
METRIC_TYPES_UNITS = {
    "cpu.system_time": (["gauge", "rate"], ["core_seconds", "cores_seconds_per_second"]),
    "cpu.total_time": (["gauge", "rate"], ["core_seconds", "cores_seconds_per_second"]),
    "cpu.user_time": (["gauge", "rate"], ["core_seconds", "cores_seconds_per_second"]),
    "mem.rss_bytes": (["gauge"], ["bytes"]),
    "mem.swap_bytes": (["gauge"], ["bytes"]),
    "mem.cache_bytes": (["gauge"], ["bytes"]),
    "mem.used_bytes": (["gauge"], ["bytes"]),
    "mem.fail_count": (["gauge"], ["count"]),
    "mem.working_set_bytes": (["gauge"], ["bytes"]),
    "fs.total_bytes": (["gauge"], ["bytes"]),
    "fs.usage_bytes": (["gauge"], ["bytes"]),
    "fs.writes": (["gauge", "rate"], ["bytes", "bytes_per_second"]),
    "fs.reads": (["gauge", "rate"], ["bytes", "bytes_per_second"]),
    "fs.io_current": (["gauge"], ["bytes"]),
    "net.in_bytes": (["gauge", "rate"], ["total_bytes", "total_bytes_per_second"]),
    "net.out_bytes": (["gauge", "rate"], ["total_bytes", "total_bytes_per_second"]),
    "net.in_packets": (["gauge", "rate"], ["total_packets", "total_packets_per_second"]),
    "net.out_packets": (["gauge", "rate"], ["total_packets", "total_packets_per_second"]),
    "net.in_dropped_packets": (["gauge", "rate"], ["total_packets", "total_packets_per_second"]),
    "net.out_dropped_packets": (["gauge", "rate"], ["total_packets", "total_packets_per_second"]),
    "net.in_errors": (["gauge", "rate"], ["total_errors", "total_errors_per_second"]),
    "net.out_errors": (["gauge", "rate"], ["total_errors", "total_errors_per_second"]),
    "io.read_bytes": (["gauge", "rate"], ["total_bytes", "total_bytes_per_second"]),
    "io.write_bytes": ("write_bytes", ["gauge", "rate"], ["total_bytes", "total_bytes_per_second"])
}


class Kubernetes(checks.AgentCheck):
    """Queries Kubelet for metadata/health data and then cAdvisor for container metrics.
    """
    def __init__(self, name, init_config, agent_config, instances=None):
        checks.AgentCheck.__init__(self, name, init_config, agent_config, instances)
        if instances is not None and len(instances) > 1:
            raise Exception('Kubernetes check only supports one configured instance.')
        self.connection_timeout = int(init_config.get('connection_timeout', DEFAULT_TIMEOUT))
        self.host = None
        self.report_container_metrics = init_config.get('report_container_metrics', REPORT_CONTAINER_METRICS)
        self.report_container_mem_percent = init_config.get('report_container_mem_percent', True)
        self.kubernetes_connector = None

    def prepare_run(self):
        """Set up Kubernetes connection information"""
        instance = self.instances[0]
        self.host = instance.get("host", None)
        derive_host = instance.get("derive_host", False)
        if not self.host:
            if derive_host:
                self.kubernetes_connector = utils.KubernetesConnector(self.connection_timeout)
                self.host = self.kubernetes_connector.get_agent_pod_host()
            else:
                exception_message = "Either host or derive host must be set when " \
                                    "running Kubernetes plugin."
                self.log.exception(exception_message)
                raise Exception(exception_message)

    def check(self, instance):
        cadvisor, kubelet = self._get_urls(instance)
        kubernetes_labels = instance.get('kubernetes_labels', ["app"])
        container_dimension_map = {}
        pod_dimensions_map = {}
        memory_limit_map = {}
        dimensions = self._set_dimensions(None, instance)
        # Remove hostname from dimensions as the majority of the metrics are not tied to the hostname.
        del dimensions['hostname']
        kubelet_health_status = self._get_api_health("{}/healthz".format(kubelet))
        self.gauge("kubelet.health_status", 0 if kubelet_health_status else 1, dimensions=dimensions)
        try:
            pods = self._get_result("{}/pods".format(kubelet))
        except Exception as e:
            self.log.exception("Error getting data from kubelet - {}".format(e))
        else:
            self._process_pods(pods['items'],
                               kubernetes_labels,
                               dimensions,
                               container_dimension_map,
                               pod_dimensions_map,
                               memory_limit_map)
            self._process_containers(cadvisor,
                                     dimensions,
                                     container_dimension_map,
                                     pod_dimensions_map,
                                     memory_limit_map)

    def _get_urls(self, instance):
        base_url = "http://{}".format(self.host)
        cadvisor_port = instance.get('cadvisor_port', DEFAULT_CADVISOR_PORT)
        kubelet_port = instance.get('kubelet_port', DEFAULT_KUBELET_PORT)
        cadvisor_url = "{}:{}".format(base_url, cadvisor_port)
        kubelet_url = "{}:{}".format(base_url, kubelet_port)
        return cadvisor_url, kubelet_url

    def _get_result(self, request_url, as_json=True):
        result = requests.get(request_url, timeout=self.connection_timeout)
        return result.json() if as_json else result

    def _get_api_health(self, health_url):
        try:
            result = self._get_result(health_url, as_json=False)
        except Exception as e:
            self.log.error("Error connecting to the health endpoint {} with exception {}".format(health_url, e))
            return False
        else:
            api_health = False
            for line in result.iter_lines():
                if line == 'ok':
                    api_health = True
                    break
            return api_health

    def _process_pods(self, pods, kubernetes_labels, dimensions, container_dimension_map, pod_dimensions_map,
                      memory_limit_map):
        for pod in pods:
            pod_status = pod['status']
            pod_spec = pod['spec']
            pod_containers = pod_spec.get('containers', None)
            container_statuses = pod_status.get('containerStatuses', None)
            if not pod_containers or not container_statuses:
                # Pod does not have any containers assigned to it no-op going to next pod
                continue
            pod_dimensions = dimensions.copy()
            pod_dimensions.update(utils.get_pod_dimensions(self.kubernetes_connector, pod['metadata'],
                                                           kubernetes_labels))
            pod_key = pod_dimensions['pod_name'] + pod_dimensions['namespace']
            pod_dimensions_map[pod_key] = pod_dimensions
            pod_retry_count = 0

            name2id = {}

            for container_status in container_statuses:
                container_restart_count = container_status['restartCount']
                container_dimensions = pod_dimensions.copy()
                container_name = container_status['name']
                container_dimensions['container_name'] = container_name
                container_dimensions['image'] = container_status['image']
                container_id = container_status.get('containerID', '').split('//')[-1]
                name2id[container_name] = container_id
                container_dimension_map[container_id] = container_dimensions
                if self.report_container_metrics:
                    container_ready = 0 if container_status['ready'] else 1
                    self.gauge("container.ready_status", container_ready, container_dimensions, hostname="SUPPRESS")
                    self.gauge("container.restart_count", container_restart_count, container_dimensions,
                               hostname="SUPPRESS")
                # getting an aggregated value for pod restart count
                pod_retry_count += container_restart_count

            # Report limit/request metrics
            if self.report_container_metrics or self.report_container_mem_percent:
                self._report_container_limits(pod_containers, container_dimension_map, name2id, memory_limit_map)

            self.gauge("pod.restart_count", pod_retry_count, pod_dimensions, hostname="SUPPRESS")
            self.gauge("pod.phase", POD_PHASE.get(pod_status['phase']), pod_dimensions, hostname="SUPPRESS")

    def _report_container_limits(self, pod_containers, container_dimension_map, name2id, memory_limit_map):
        for container in pod_containers:
            container_name = container['name']
            container_dimensions = container_dimension_map[name2id[container_name]]
            if 'resources' not in container:
                self.log.debug("Container {} does not have limits or requests set")
                continue
            container_resources = container['resources']
            if 'limits' not in container_resources:
                self.log.debug("Container {} does not have limits set", container_name)
            else:
                container_limits = container_resources['limits']
                if 'cpu' in container_limits:
                    cpu_limit = container_limits['cpu']
                    cpu_value = self._convert_cpu_to_cores(cpu_limit)
                    if self.report_container_metrics:
                        self.gauge("container.cpu.limit", cpu_value, container_dimensions, hostname="SUPPRESS")
                else:
                    self.log.debug("Container {} does not have cpu limit set", container_name)
                if 'memory' in container_limits:
                    memory_limit = container_limits['memory']
                    memory_in_bytes = utils.convert_memory_string_to_bytes(memory_limit)
                    if self.report_container_metrics:
                        self.gauge("container.memory.limit_bytes", memory_in_bytes, container_dimensions,
                                   hostname="SUPPRESS")
                    if self.report_container_mem_percent:
                        container_key = container_name + " " + container_dimensions["namespace"]
                        if container_key not in memory_limit_map:
                            memory_limit_map[container_key] = memory_in_bytes
                else:
                    self.log.debug("Container {} does not have memory limit set", container_name)
            if 'requests' not in container_resources:
                self.log.debug("Container {} does not have requests set", container_name)
            else:
                container_requests = container_resources['requests']
                if 'cpu' in container_requests:
                    cpu_request = container_requests['cpu']
                    cpu_value = self._convert_cpu_to_cores(cpu_request)
                    if self.report_container_metrics:
                        self.gauge("container.request.cpu", cpu_value, container_dimensions, hostname="SUPPRESS")
                else:
                    self.log.debug("Container {} does not have cpu request set", container_name)
                if 'memory' in container_requests:
                    memory_request = container_requests['memory']
                    memory_in_bytes = utils.convert_memory_string_to_bytes(memory_request)
                    if self.report_container_metrics:
                        self.gauge("container.request.memory_bytes", memory_in_bytes, container_dimensions,
                                   hostname="SUPPRESS")
                else:
                    self.log.debug("Container {} does not have memory request set", container_name)

    def _convert_cpu_to_cores(self, cpu_string):
        """Kubernetes reports cores in millicores in some instances.
        This method makes sure when we report on cpu they are all in cores
        """
        if "m" in cpu_string:
            cpu = float(cpu_string.split('m')[0])
            return cpu / 1000
        return float(cpu_string)

    def _send_metrics(self, metric_name, value, dimensions, metric_types,
                      metric_units):
        for metric_type in metric_types:
            if metric_type == 'rate':
                dimensions.update({'unit': metric_units[
                    metric_types.index('rate')]})
                self.rate(metric_name + "_sec", value, dimensions,
                          hostname="SUPPRESS" if "pod_name" in dimensions else None)
            elif metric_type == 'gauge':
                dimensions.update({'unit': metric_units[
                    metric_types.index('gauge')]})
                self.gauge(metric_name, value, dimensions,
                           hostname="SUPPRESS" if "pod_name" in dimensions else None)

    def _parse_memory(self, memory_data, container_dimensions, pod_key, pod_map, memory_limit_map):
        memory_metrics = CADVISOR_METRICS['memory_metrics']
        for cadvisor_key, metric_name in memory_metrics.items():
            if cadvisor_key in memory_data:
                metric_value = memory_data[cadvisor_key]
                if self.report_container_metrics:
                    self._send_metrics("container." + metric_name,
                                       metric_value,
                                       container_dimensions,
                                       METRIC_TYPES_UNITS[metric_name][0],
                                       METRIC_TYPES_UNITS[metric_name][1])
                self._add_pod_metric(metric_name, metric_value, pod_key, pod_map)
                if self.report_container_mem_percent and cadvisor_key == "working_set":
                    if "container_name" in container_dimensions and "namespace" in container_dimensions:
                        container_key = container_dimensions["container_name"] + " " + container_dimensions["namespace"]
                        if container_key not in memory_limit_map:
                            continue
                        memory_limit = memory_limit_map[container_key]
                        memory_usage = metric_value
                        memory_usage_percent = (memory_usage / memory_limit) * 100
                        self.gauge("container.mem.usage_percent", memory_usage_percent, container_dimensions,
                                   hostname="SUPPRESS")

    def _parse_filesystem(self, filesystem_data, container_dimensions):
        if not self.report_container_metrics:
            return
        filesystem_metrics = CADVISOR_METRICS['filesystem_metrics']
        for filesystem in filesystem_data:
            file_dimensions = container_dimensions.copy()
            file_dimensions['device'] = filesystem['device']
            for cadvisor_key, metric_name in filesystem_metrics.items():
                if cadvisor_key in filesystem:
                    self._send_metrics("container." + metric_name,
                                       filesystem[cadvisor_key],
                                       file_dimensions,
                                       METRIC_TYPES_UNITS[metric_name][0],
                                       METRIC_TYPES_UNITS[metric_name][1])

    def _parse_network(self, network_data, container_dimensions, pod_key, pod_metrics):
        if 'interfaces' not in network_data:
            return
        network_interfaces = network_data['interfaces']
        network_metrics = CADVISOR_METRICS['network_metrics']
        sum_network_interfaces = {}
        for interface in network_interfaces:
            sum_network_interfaces = rollup_dictionaries(
                sum_network_interfaces, interface)
        for cadvisor_key, metric_name in network_metrics.items():
            if cadvisor_key in sum_network_interfaces:
                metric_value = sum_network_interfaces[cadvisor_key]
                if self.report_container_metrics:
                    self._send_metrics("container." + metric_name,
                                       metric_value,
                                       container_dimensions,
                                       METRIC_TYPES_UNITS[metric_name][0],
                                       METRIC_TYPES_UNITS[metric_name][1])
                self._add_pod_metric(metric_name, metric_value, pod_key,
                                     pod_metrics)

    def _parse_cpu(self, cpu_data, container_dimensions, pod_key, pod_metrics):
        cpu_metrics = CADVISOR_METRICS['cpu_metrics']
        cpu_usage = cpu_data['usage']
        for cadvisor_key, metric_name in cpu_metrics.items():
            if cadvisor_key in cpu_usage:
                # convert nanoseconds to seconds
                cpu_usage_sec = cpu_usage[cadvisor_key] / 1000000000
                if self.report_container_metrics:
                    self._send_metrics("container." + metric_name,
                                       cpu_usage_sec,
                                       container_dimensions,
                                       METRIC_TYPES_UNITS[metric_name][0],
                                       METRIC_TYPES_UNITS[metric_name][1])
                self._add_pod_metric(metric_name, cpu_usage_sec, pod_key, pod_metrics)

    def _parse_diskio(self, diskio_data, container_dimensions, pod_key, pod_metrics):
        diskio_services = diskio_data['io_service_bytes']
        diskio_metrics = CADVISOR_METRICS['diskio_metrics']
        sum_diskio_devices = {}
        for disk_device in diskio_services:
            sum_diskio_devices = rollup_dictionaries(
                sum_diskio_devices, disk_device['stats'])

        for cadvisor_key, metric_name in diskio_metrics.items():
            if cadvisor_key in sum_diskio_devices:
                metric_value = sum_diskio_devices[cadvisor_key]
                if self.report_container_metrics:
                    self._send_metrics("container." + metric_name,
                                       metric_value,
                                       container_dimensions,
                                       METRIC_TYPES_UNITS[metric_name][0],
                                       METRIC_TYPES_UNITS[metric_name][1])
                self._add_pod_metric(metric_name, metric_value, pod_key,
                                     pod_metrics)

    def _add_pod_metric(self, metric_name, metric_value, pod_key, pod_metrics):
            if pod_key:
                if pod_key not in pod_metrics:
                    pod_metrics[pod_key] = {}
                if metric_name not in pod_metrics[pod_key]:
                    pod_metrics[pod_key][metric_name] = metric_value
                else:
                    pod_metrics[pod_key][metric_name] += metric_value

    def _get_container_dimensions(self, container, instance_dimensions, container_spec, container_dimension_map,
                                  pod_dimension_map):
        container_id = ""
        # meant to key through pod metrics/dimension dictionaries

        for alias in container_spec["aliases"]:
            if alias in container:
                container_id = alias
                break
        if container_id in container_dimension_map:
            container_dimensions = container_dimension_map[container_id]
            pod_key = container_dimensions['pod_name'] + container_dimensions['namespace']
            return pod_key, container_dimensions
        else:
            container_dimensions = instance_dimensions.copy()
            # Container image being used
            container_dimensions['image'] = container_spec['image']
            # First entry in aliases is container name
            container_dimensions['container_name'] = container_spec['aliases'][0]
            # check if container is a pause container running under a pod. Owns network namespace
            pod_key = None
            if 'labels' in container_spec:
                container_labels = container_spec['labels']
                if 'io.kubernetes.pod.namespace' in container_labels and 'io.kubernetes.pod.name' in container_labels:
                    pod_key = container_labels['io.kubernetes.pod.name'] + \
                        container_labels['io.kubernetes.pod.namespace']
                    # In case new pods showed up since we got our pod list from the kubelet
                    if pod_key in pod_dimension_map:
                        container_dimensions.update(pod_dimension_map[pod_key])
                        container_dimensions['container_name'] = container_labels['io.kubernetes.container.name']
                    else:
                        pod_key = None
            return pod_key, container_dimensions

    def _process_containers(self, cadvisor_url, dimensions, container_dimension_map, pod_dimension_map,
                            memory_limit_map):
        try:
            cadvisor_spec_url = cadvisor_url + CADVISOR_SPEC_URL
            cadvisor_metric_url = cadvisor_url + CADVISOR_METRIC_URL
            containers_spec = self._get_result(cadvisor_spec_url)
            containers_metrics = self._get_result(cadvisor_metric_url)
        except Exception as e:
            self.log.error("Error getting data from cadvisor - {}".format(e))
            return
        pod_metrics = {}
        for container, cadvisor_metrics in containers_metrics.items():
            pod_key, container_dimensions = self._get_container_dimensions(
                container,
                dimensions,
                containers_spec[container],
                container_dimension_map,
                pod_dimension_map)
            # Grab first set of metrics from return data
            cadvisor_metrics = cadvisor_metrics[0]
            if cadvisor_metrics['has_memory'] and cadvisor_metrics['memory']:
                self._parse_memory(cadvisor_metrics['memory'],
                                   container_dimensions,
                                   pod_key,
                                   pod_metrics,
                                   memory_limit_map)
            if cadvisor_metrics['has_filesystem'] and 'filesystem' in cadvisor_metrics \
                    and cadvisor_metrics['filesystem']:
                self._parse_filesystem(cadvisor_metrics['filesystem'],
                                       container_dimensions)
            if cadvisor_metrics['has_network'] and cadvisor_metrics['network']:
                self._parse_network(cadvisor_metrics['network'],
                                    container_dimensions,
                                    pod_key,
                                    pod_metrics)
            if cadvisor_metrics['has_cpu'] and cadvisor_metrics['cpu']:
                self._parse_cpu(cadvisor_metrics['cpu'],
                                container_dimensions,
                                pod_key,
                                pod_metrics)
            if cadvisor_metrics['has_diskio'] and cadvisor_metrics['diskio']:
                self._parse_diskio(cadvisor_metrics['diskio'],
                                   container_dimensions,
                                   pod_key,
                                   pod_metrics)
        self.send_pod_metrics(pod_metrics, pod_dimension_map)

    def send_pod_metrics(self, pod_metrics_map, pod_dimension_map):
        for pod_key, pod_metrics in pod_metrics_map.items():
            pod_dimensions = pod_dimension_map[pod_key]
            for metric_name, metric_value in pod_metrics.items():
                self._send_metrics("pod." + metric_name,
                                   metric_value,
                                   pod_dimensions,
                                   METRIC_TYPES_UNITS[metric_name][0],
                                   METRIC_TYPES_UNITS[metric_name][1])
