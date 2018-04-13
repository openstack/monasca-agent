# (C) Copyright 2017 Hewlett Packard Enterprise Development Company LP
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

import unittest

import os

import monasca_agent.common.config as configuration
import monasca_agent.common.metrics as metrics_pkg

from monasca_agent.collector.checks import AgentCheck

base_config = configuration.Config(os.path.join(os.path.dirname(__file__),
                                                'test-agent.yaml'))


class TestAgentCheck(unittest.TestCase):
    def testBadMetricKeepBatch(self):
        agent_config = base_config.get_config(sections='Main')

        check = AgentCheck("foo", {}, agent_config)

        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        check.submit_metric("Foo",
                            5,
                            metrics_pkg.Gauge,
                            dimensions=dimensions,
                            delegated_tenant=None,
                            hostname=None,
                            device_name=None,
                            value_meta=None)
        self.assertEqual(len(check.aggregator.metrics), 1)

        dimensions = {'A': '{}', 'B': 'C', 'D': 'E'}
        check.submit_metric("Bar",
                            5,
                            metrics_pkg.Gauge,
                            dimensions=dimensions,
                            delegated_tenant=None,
                            hostname=None,
                            device_name=None,
                            value_meta=None)
        self.assertEqual(len(check.aggregator.metrics), 1)

        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        check.submit_metric("Baz",
                            5,
                            metrics_pkg.Gauge,
                            dimensions=dimensions,
                            delegated_tenant=None,
                            hostname=None,
                            device_name=None,
                            value_meta=None)
        self.assertEqual(len(check.aggregator.metrics), 2)
