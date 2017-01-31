# (C) Copyright 2017 Hewlett Packard Enterprise Development LP

import mock
import unittest

from monasca_agent.collector.checks_d.kubernetes_api import KubernetesAPI

SUCCESS = 0
FAILURE = 1
KUBERNETES_LABELS = ['app']


class TestKubernetesAPI(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        init_config = {}
        agent_config = {}
        self._kubernetes_api = KubernetesAPI('TestKubernetesAPI',
                                             init_config,
                                             agent_config)
        self._gauge = mock.Mock()
        self._kubernetes_api.gauge = self._gauge
        self._hostname = 'SUPPRESS'
        self._instance = {'derive_api_url': True}
        self._base_dimensions = {}

    def _get_api_health_check(self, instance, result_input):
        mock_check = mock.Mock(return_value=result_input)
        self._kubernetes_api._get_api_health = mock_check
        self._kubernetes_api.check(instance)

    def test_kubernetes_api_is_healthy(self):
        api_health_result = True
        self._get_api_health_check(self._instance,
                                   api_health_result)
        self._gauge.assert_called_with('kubernetes.api.health_status',
                                       SUCCESS,
                                       self._base_dimensions,
                                       hostname=self._hostname)

    def test_kubernetes_api_is_not_healthy(self):
        api_health_result = False
        self._get_api_health_check(self._instance,
                                   api_health_result)

        self._gauge.assert_called_with('kubernetes.api.health_status',
                                       FAILURE,
                                       self._base_dimensions,
                                       hostname=self._hostname)

    def _send_request(self, result_input):
        mock_check = mock.Mock(return_value=result_input)
        self._kubernetes_api._send_request = mock_check

    def test_report_cluster_component_statuses(self):
        component_statuses_request_result = {
            u'items': [
                {u'conditions': [{
                    u'status': u'True',
                    u'message': u'{"health": "true"}',
                    u'type': u'Healthy'}],
                 u'metadata': {u'creationTimestamp': None,
                               u'name': u'etcd-0'}}],
            u'kind': u'ComponentStatusList',
            u'apiVersion': u'v1',
            u'metadata': {u'selfLink': u'/api/v1/componentstatuses'}}
        self._send_request(component_statuses_request_result)
        self._kubernetes_api._report_cluster_component_statuses(
            self._base_dimensions)
        self._gauge.assert_called_with('kubernetes.component_status',
                                       SUCCESS,
                                       {'component_name': u'etcd-0'},
                                       hostname=self._hostname)

    def test_nodes_capacity_metric(self):
        nodes_request_result = {
            u'items': [
                {u'status': {
                    u'capacity': {u'cpu': u'4'},
                    u'allocatable': {},
                    u'daemonEndpoints': {
                        u'kubeletEndpoint': {u'Port': 10250}},
                    u'images': [{u'sizeBytes': 821774423,
                                 u'names': [u'image_name',
                                            u'image_name:latest']}],
                    u'conditions': [{u'status': u'False',
                                     u'type': u'OutOfDisk'}]},
                    u'metadata': {u'name': u'node01',
                                  u'uid': u'e3600619-2557-11e7-9d76-aab101'}}]}
        self._send_request(nodes_request_result)
        self._kubernetes_api._report_nodes_metrics(self._base_dimensions)
        self._gauge.assert_called_with('kubernetes.node.capacity.cpu',
                                       4.0,
                                       {'hostname': u'node01',
                                        'unit': 'cores'})

    def test_nodes_allocatable_metric(self):
        nodes_request_result = {
            u'items': [
                {u'status': {
                    u'capacity': {},
                    u'allocatable': {
                        u'alpha.kubernetes.io/nvidia-gpu': u'0',
                        u'pods': u'110'},
                    u'daemonEndpoints': {
                        u'kubeletEndpoint': {u'Port': 10250}},
                    u'images': [{u'sizeBytes': 821774423,
                                 u'names': [u'image_name',
                                            u'image_name:latest']}],
                    u'conditions': [{u'status': u'False',
                                     u'type': u'OutOfDisk'},
                                    {u'status': u'False',
                                     u'type': u'MemoryPressure'},
                                    {u'status': u'False',
                                     u'type': u'DiskPressure'},
                                    {u'status': u'True',
                                     u'type': u'Ready'}]},
                    u'metadata': {u'name': u'node01',
                                  u'uid': u'e3600619-2557-11e7-9d76-aa3201'}}]}
        self._send_request(nodes_request_result)
        self._kubernetes_api._report_nodes_metrics(self._base_dimensions)
        self._gauge.assert_called_with('kubernetes.node.allocatable.pods',
                                       110.0,
                                       {'hostname': u'node01'})

    def test_deployment_metrics(self):
        deployments_request_result = {
            u'items': [
                {u'status': {
                    u'observedGeneration': 1,
                    u'updatedReplicas': 2,
                    u'availableReplicas': 3,
                    u'replicas': 4
                    },
                 u'metadata': {u'name': u'kube-controller-manager',
                               u'labels': {
                                   u'k8s-app': u'kube-controller-manager'},
                               u'namespace': u'kube-system',
                               u'uid': u'e61835b9-2557-11e7-9d76-aabbcc201'}}]}
        self._send_request(deployments_request_result)
        self._kubernetes_api._report_deployment_metrics(self._base_dimensions,
                                                        KUBERNETES_LABELS)
        self._gauge.assert_called_with(
            'kubernetes.deployment.updated_replicas', 2,
            {'type': u'kube-controller-manager',
             'namespace': u'kube-system'},
            hostname=self._hostname)
