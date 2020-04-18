# Copyright (c) 2018 StackHPC Ltd.
#
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

from unittest import mock
import unittest


import monasca_agent.collector.checks_d.ib_network as ib_network


class MockIBNetworkPlugin(ib_network.IBNetwork):
    def __init__(self):
        # Don't call the base class constructor
        pass

    @staticmethod
    def _set_dimensions(dimensions, instance=None):
        return {'hostname': 'dummy_hostname'}

    @staticmethod
    def _get_devices():
        return ['mlx5_0', 'mlx5_1']

    @staticmethod
    def _get_fields(device):
        return ['port_rcv_data', 'port_rcv_pkts']


class TestIBNetwork(unittest.TestCase):
    def setUp(self):
        self.ib_network = MockIBNetworkPlugin()

    @mock.patch('monasca_agent.collector.checks_d.ib_network.open',
                mock.mock_open(read_data='1024'))
    @mock.patch('monasca_agent.collector.checks.AgentCheck.rate',
                autospec=True)
    def test_check(self, mock_rate):
        self.ib_network.check(None)
        # For each of the two dummy devices we expect to collect two dummy
        # fields. The count for port_rcv_data should be multiplied by the lane
        # count.
        calls = [
            mock.call(
                mock.ANY,
                ib_network._METRIC_NAME_PREFIX + '.port_rcv_data',
                4096,
                device_name='mlx5_0',
                dimensions={'hostname': 'dummy_hostname'}
            ),
            mock.call(
                mock.ANY,
                ib_network._METRIC_NAME_PREFIX + '.port_rcv_pkts',
                1024,
                device_name='mlx5_0',
                dimensions={'hostname': 'dummy_hostname'}
            ),
            mock.call(
                mock.ANY,
                ib_network._METRIC_NAME_PREFIX + '.port_rcv_data',
                4096,
                device_name='mlx5_1',
                dimensions={'hostname': 'dummy_hostname'}
            ),
            mock.call(
                mock.ANY,
                ib_network._METRIC_NAME_PREFIX + '.port_rcv_pkts',
                1024,
                device_name='mlx5_1',
                dimensions={'hostname': 'dummy_hostname'}
            ),
        ]
        mock_rate.assert_has_calls(calls, any_order=True)
