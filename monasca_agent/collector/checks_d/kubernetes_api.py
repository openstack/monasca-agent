# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import requests

from monasca_agent.collector import checks
from monasca_agent.collector.checks import utils

DEFAULT_TIMEOUT = 5
NODE_CONDITIONS_MAP = {
    "OutOfDisk": {
        "metric_name": "node.out_of_disk",
        "expected_status": "False"
    },
    "MemoryPressure": {
        "metric_name": "node.memory_pressure",
        "expected_status": "False"
    },
    "DiskPressure": {
        "metric_name": "node.disk_pressure",
        "expected_status": "False"
    },
    "Ready": {
        "metric_name": "node.ready_status",
        "expected_status": "True"
    }
}


class KubernetesAPI(checks.AgentCheck):
    """Queries Kubernetes API to get metrics about the Kubernetes deployment
    """
    def __init__(self, name, init_config, agent_config, instances=None):
        checks.AgentCheck.__init__(self, name, init_config, agent_config, instances)
        if instances is not None and len(instances) > 1:
            raise Exception('Kubernetes api check only supports one configured instance.')
        self.connection_timeout = int(init_config.get('connection_timeout', DEFAULT_TIMEOUT))
        self.kubernetes_connector = None
        self.kubernetes_api = None

    def prepare_run(self):
        """Set up Kubernetes connection information"""
        instance = self.instances[0]
        host = instance.get("host", None)
        derive_api_url = instance.get("derive_api_url", None)
        if not host:
            if derive_api_url:
                self.kubernetes_connector = utils.KubernetesConnector(self.connection_timeout)
            else:
                exception_message = "Either Kubernetes API url (host and port)" \
                                    " or derive_api_url=True must be set" \
                                    " when running Kubernetes API plugin."
                self.log.error(exception_message)
                raise Exception(exception_message)
        else:
            kubernetes_api_port = instance.get("kubernetes_api_port", "8080")
            self.kubernetes_api = "http://{}:{}".format(host, kubernetes_api_port)

    def check(self, instance):
        kubernetes_labels = instance.get('kubernetes_labels', ["app"])
        dimensions = self._set_dimensions(None, instance)
        # Remove hostname from dimensions as the majority of the metrics are not
        # tied to the hostname.
        del dimensions['hostname']
        kubernetes_api_health = self._get_api_health()
        self.gauge("kubernetes.api.health_status", 0 if kubernetes_api_health else 1, dimensions,
                   hostname="SUPPRESS")
        self._report_cluster_component_statuses(dimensions)
        self._report_nodes_metrics(dimensions)
        self._report_deployment_metrics(dimensions, kubernetes_labels)
        self._report_replication_controller_metrics(dimensions, kubernetes_labels)

    def _send_request(self, endpoint, as_json=True):
        if self.kubernetes_connector:
            return self.kubernetes_connector.get_request(endpoint, as_json=as_json)
        else:
            result = requests.get("{}/{}".format(self.kubernetes_api, endpoint))
            return result.json() if as_json else result

    def _get_api_health(self):
        try:
            result = self._send_request("healthz", as_json=False)
        except Exception as e:
            self.log.error("Error connecting to the health endpoint with exception {}".format(e))
            return False
        else:
            # Return true if 'ok' is in result
            return 'ok' in result.iter_lines()

    def _report_cluster_component_statuses(self, dimensions):
        try:
            component_statuses = self._send_request("/api/v1/componentstatuses")
        except Exception as e:
            self.log.error("Error getting data from Kubernetes API - {}".format(e))
            return
        for component in component_statuses['items']:
            component_dimensions = dimensions.copy()
            component_dimensions['component_name'] = component['metadata']['name']
            component_status = False
            component_conditions = component['conditions']
            for condition in component_conditions:
                if 'type' in condition and condition['type'] == 'Healthy':
                    if condition['status']:
                        component_status = True
                        break
            self.gauge(
                "kubernetes.component_status",
                0 if component_status else 1,
                component_dimensions,
                hostname="SUPPRESS")

    def _set_kubernetes_dimensions(self, dimensions, type, metadata, kubernetes_labels):
        dimensions['type'] = metadata['name']
        dimensions['namespace'] = metadata['namespace']
        if 'labels' in metadata:
            labels = metadata['labels']
            for label in kubernetes_labels:
                if label in labels:
                    dimensions[label] = labels[label]

    def _report_node_resource_metrics(self, resource, metrics, node_dimensions):
        resource_metrics_dimensions = node_dimensions.copy()
        for metric_name, metric_value in metrics.items():
            if "gpu" in metric_name:
                continue
            if metric_name == "memory":
                metric_name += "_bytes"
                metric_value = utils.convert_memory_string_to_bytes(metric_value)
                resource_metrics_dimensions.update({'unit': 'bytes'})
            elif metric_name == "cpu":
                resource_metrics_dimensions.update({'unit': 'cores'})
            metric_name = "kubernetes.node.{}.{}".format(resource, metric_name)
            self.gauge(metric_name, float(metric_value), resource_metrics_dimensions)

    def _report_node_conditions_metrics(self, node_conditions, node_dimensions):
        for condition in node_conditions:
            condition_type = condition["type"]
            if condition_type in NODE_CONDITIONS_MAP:
                condition_map = NODE_CONDITIONS_MAP[condition_type]
                condition_status = condition['status']
                if condition_status == condition_map['expected_status']:
                    self.gauge("kubernetes." + condition_map['metric_name'], 0, node_dimensions)
                else:
                    value_meta = {"reason": condition['message'][:1024]}
                    self.gauge(
                        "kubernetes." +
                        condition_map['metric_name'],
                        1,
                        node_dimensions,
                        value_meta=value_meta)

    def _report_nodes_metrics(self, dimensions):
        try:
            nodes = self._send_request("/api/v1/nodes")
        except Exception as e:
            self.log.error("Error getting node data from Kubernetes API - {}".format(e))
            return
        for node in nodes['items']:
            node_dimensions = dimensions.copy()
            node_dimensions['hostname'] = node['metadata']['name']
            node_status = node['status']
            self._report_node_conditions_metrics(node_status['conditions'], node_dimensions)
            if 'spec' in node and 'unschedulable' in node['spec']:
                if node['spec']['unschedulable']:
                    continue
            node_capacity = node_status['capacity']
            node_allocatable = node_status['allocatable']
            self._report_node_resource_metrics('capacity', node_capacity, node_dimensions)
            self._report_node_resource_metrics('allocatable', node_allocatable, node_dimensions)

    def _report_deployment_metrics(self, dimensions, kubernetes_labels):
        try:
            deployments = self._send_request("/apis/extensions/v1beta1/deployments")
        except Exception as e:
            self.log.error("Error getting deployment data from Kubernetes API - {}".format(e))
            return
        for deployment in deployments['items']:
            try:
                deployment_dimensions = dimensions.copy()
                self._set_kubernetes_dimensions(
                    deployment_dimensions,
                    "deployment",
                    deployment['metadata'],
                    kubernetes_labels)
                deployment_status = deployment['status']
                deployment_replicas = deployment_status['replicas']
                deployment_updated_replicas = deployment_status['updatedReplicas']
                deployment_available_replicas = deployment_status['availableReplicas']
                deployment_unavailable_replicas = \
                    deployment_available_replicas - deployment_replicas
                self.gauge("kubernetes.deployment.replicas", deployment_replicas,
                           deployment_dimensions, hostname="SUPPRESS")
                self.gauge(
                    "kubernetes.deployment.available_replicas",
                    deployment_available_replicas,
                    deployment_dimensions,
                    hostname="SUPPRESS")
                self.gauge(
                    "kubernetes.deployment.unavailable_replicas",
                    deployment_unavailable_replicas,
                    deployment_dimensions,
                    hostname="SUPPRESS")
                self.gauge("kubernetes.deployment.updated_replicas", deployment_updated_replicas,
                           deployment_dimensions, hostname="SUPPRESS")
            except Exception as e:
                self.log.info(
                    "Error {} parsing deployment {}. Skipping".format(
                        e, deployment), exc_info=e)

    def _report_replication_controller_metrics(self, dimensions, kubernetes_labels):
        # Get namespaces first
        try:
            namespaces = self._send_request("/api/v1/namespaces")
        except Exception as e:
            self.log.error("Error getting namespaces from API - {}. "
                           "Skipping getting replication controller metrics".format(e))
            return
        for namespace in namespaces['items']:
            namespace_name = namespace['metadata']['name']
            try:
                replication_controllers = self._send_request(
                    "/api/v1/namespaces/{}/replicationcontrollers".format(namespace_name))
            except Exception as e:
                self.log.error("Error getting replication controllers for the namespace {} "
                               "with the error {}".format(namespace, e))
                continue
            if 'items' not in replication_controllers:
                continue
            for rc in replication_controllers['items']:
                rc_dimensions = dimensions.copy()
                self._set_kubernetes_dimensions(
                    rc_dimensions,
                    "replication_controller",
                    rc['metadata'],
                    kubernetes_labels)
                rc_status = rc['status']
                if 'replicas' not in rc_status or not rc_status['replicas']:
                    continue
                self.gauge("kubernetes.replication.controller.replicas", rc_status['replicas'],
                           rc_dimensions, hostname="SUPPRESS")
                self.gauge(
                    "kubernetes.replication.controller.ready_replicas",
                    rc_status['readyReplicas'],
                    rc_dimensions,
                    hostname="SUPPRESS")
