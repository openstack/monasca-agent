# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
import requests

from monasca_agent.collector.checks import AgentCheck
from monasca_agent.collector.checks import utils
from monasca_agent.common.util import rollup_dictionaries

DEFAULT_TIMEOUT = "3"

# format for METRICS: (cadvisor metric name, [metric types], [metric units])
METRICS = {
    "cpu_metrics": {
        "system": ("system_time", ["gauge", "rate"],
                   ["core_seconds", "core_seconds_per_second"]),
        "total": ("total_time", ["gauge", "rate"],
                  ["core_seconds", "core_seconds_per_second"]),
        "user": ("user_time", ["gauge", "rate"],
                 ["core_seconds", "core_seconds_per_second"])
    },
    "memory_metrics": {
        "swap": ("swap_bytes", ["gauge"], ["bytes"]),
        "cache": ("cache_bytes", ["gauge"], ["bytes"]),
        "usage": ("used_bytes", ["gauge"], ["bytes"]),
    },
    "filesystem_metrics": {
        "capacity": ("total_bytes", ["gauge"], ["bytes"]),
        "usage": ("usage_bytes", ["gauge"], ["bytes"])
    },
    'network_metrics': {
        "rx_bytes": ("in_bytes", ["gauge", "rate"],
                     ["total_bytes", "total_bytes_per_second"]),
        "tx_bytes": ("out_bytes", ["gauge", "rate"],
                     ["total_bytes", "total_bytes_per_second"]),
        "rx_packets": ("in_packets", ["gauge", "rate"],
                       ["total_packets", "total_packets_per_second"]),
        "tx_packets": ("out_packets", ["gauge", "rate"],
                       ["total_packets", "total_packets_per_second"]),
        "rx_dropped": ("in_dropped_packets", ["gauge", "rate"],
                       ["total_packets", "total_packets_per_second"]),
        "tx_dropped": ("out_dropped_packets", ["gauge", "rate"],
                       ["total_packets", "total_packets_per_second"]),
        "rx_errors": ("in_errors", ["gauge", "rate"],
                      ["total_errors", "total_errors_per_second"]),
        "tx_errors": ("out_errors", ["gauge", "rate"],
                      ["total_errors", "total_errors_per_second"])
    },
    "diskio_metrics": {
        "Read": ("read_bytes", ["gauge", "rate"],
                 ["total_bytes", "total_bytes_per_second"]),
        'Write': ("write_bytes", ["gauge", "rate"],
                  ["total_bytes", "total_bytes_per_second"])
    },
}


class CadvisorHost(AgentCheck):
    """Queries given cAdvisor API for node metrics
    """

    def __init__(self, name, init_config, agent_config, instances=None):
        AgentCheck.__init__(self, name, init_config, agent_config, instances)
        if instances is not None and len(instances) > 1:
            raise Exception('cAdvisor host check only supports one configured'
                            ' instance.')
        self.connection_timeout = int(init_config.get('connection_timeout',
                                                      DEFAULT_TIMEOUT))
        self.cadvisor_url = None

    def check(self, instance):
        if not self.cadvisor_url:
            cadvisor_url = instance.get("cadvisor_url", None)
            detect_cadvisor_url = instance.get("kubernetes_detect_cadvisor", False)
            if not cadvisor_url:
                if detect_cadvisor_url:
                    kubernetes_connector = utils.KubernetesConnector(self.connection_timeout)
                    host = kubernetes_connector.get_agent_pod_host()
                    cadvisor_url = "http://{}:4194".format(host)
                else:
                    exception_message = "Either cAdvisor url or kubernetes " \
                                        "detect cAdvisor must be set when " \
                                        "monitoring a Kubernetes Node."
                    self.log.error(exception_message)
                    raise Exception(exception_message)
            self.cadvisor_url = "{}/{}".format(cadvisor_url, "api/v2.0/stats?count=1")
        dimensions = self._set_dimensions(None, instance)
        try:
            host_metrics = requests.get(self.cadvisor_url, self.connection_timeout).json()
        except Exception as e:
            self.log.error("Error communicating with cAdvisor to collect data - {}".format(e))
        else:
            self._parse_send_metrics(host_metrics, dimensions)

    def _send_metrics(self, metric_name, value, dimensions, metric_types,
                      metric_units):
        for metric_type in metric_types:
            if metric_type == 'rate':
                dimensions.update({'unit': metric_units[metric_types.index('rate')]})
                self.rate(metric_name + "_sec", value, dimensions)
            elif metric_type == 'gauge':
                dimensions.update({'unit': metric_units[metric_types.index('gauge')]})
                self.gauge(metric_name, value, dimensions)

    def _parse_memory(self, memory_data, dimensions):
        memory_metrics = METRICS['memory_metrics']
        for cadvisor_key, (metric_name, metric_types, metric_units) in memory_metrics.items():
            if cadvisor_key in memory_data:
                self._send_metrics("mem." + metric_name,
                                   memory_data[cadvisor_key],
                                   dimensions,
                                   metric_types, metric_units)

    def _parse_filesystem(self, filesystem_data, dimensions):
        filesystem_metrics = METRICS['filesystem_metrics']
        for filesystem in filesystem_data:
            file_dimensions = dimensions.copy()
            file_dimensions['device'] = filesystem['device']
            for cadvisor_key, (metric_name, metric_types, metric_units) in filesystem_metrics.items():
                if cadvisor_key in filesystem:
                    self._send_metrics("fs." + metric_name,
                                       filesystem[cadvisor_key],
                                       file_dimensions,
                                       metric_types, metric_units)

    def _parse_network(self, network_data, dimensions):
        network_interfaces = network_data['interfaces']
        network_metrics = METRICS['network_metrics']
        interface_sum = {}
        # This function is to roll up network metrics for different interfaces
        for interface in network_interfaces:
            interface_sum = rollup_dictionaries(interface_sum, interface)

        network_dimensions = dimensions.copy()
        for cadvisor_key, (metric_name, metric_types, metric_units) in network_metrics.items():
            if cadvisor_key in interface_sum:
                self._send_metrics("net." + metric_name,
                                   interface_sum[cadvisor_key],
                                   network_dimensions,
                                   metric_types,
                                   metric_units)

    def _parse_diskio(self, diskio_data, dimensions):
        diskio_metrics = METRICS['diskio_metrics']
        disk_io_sum = {}
        for io_data in diskio_data['io_service_bytes']:
            disk_io_sum = rollup_dictionaries(disk_io_sum, io_data['stats'])

        for cadvisor_key, (metric_name, metric_types, metric_units) in diskio_metrics.items():
            if cadvisor_key in disk_io_sum:
                self._send_metrics("io." + metric_name, disk_io_sum[cadvisor_key],
                                   dimensions,
                                   metric_types,
                                   metric_units)

    def _parse_cpu(self, cpu_data, dimensions):
        cpu_metrics = METRICS['cpu_metrics']
        cpu_usage = cpu_data['usage']
        for cadvisor_key, (metric_name, metric_types, metric_units) in cpu_metrics.items():
            if cadvisor_key in cpu_usage:
                # Convert nanoseconds to seconds
                cpu_usage_sec = cpu_usage[cadvisor_key] / 1000000000.0
                self._send_metrics("cpu." + metric_name, cpu_usage_sec, dimensions, metric_types, metric_units)

    def _parse_send_metrics(self, metrics, dimensions):
        for host, cadvisor_metrics in metrics.items():
            host_dimensions = dimensions.copy()
            # Grab first set of metrics from return data
            cadvisor_metrics = cadvisor_metrics[0]
            if cadvisor_metrics['has_memory'] and cadvisor_metrics['memory']:
                self._parse_memory(cadvisor_metrics['memory'], host_dimensions)
            if cadvisor_metrics['has_filesystem'] and cadvisor_metrics['filesystem']:
                self._parse_filesystem(cadvisor_metrics['filesystem'], host_dimensions)
            if cadvisor_metrics['has_network'] and cadvisor_metrics['network']:
                self._parse_network(cadvisor_metrics['network'], host_dimensions)
            if cadvisor_metrics['has_diskio'] and cadvisor_metrics['diskio']:
                self._parse_diskio(cadvisor_metrics['diskio'], host_dimensions)
            if cadvisor_metrics['has_cpu'] and cadvisor_metrics['cpu']:
                self._parse_cpu(cadvisor_metrics['cpu'], host_dimensions)
