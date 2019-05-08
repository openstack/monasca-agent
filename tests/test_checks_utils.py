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

import os
import time
import unittest

import monasca_agent.common.config as configuration
from monasca_agent.collector.checks import AgentCheck
from monasca_agent.collector.checks.utils import DynamicCheckHelper

base_config = configuration.Config(os.path.join(os.path.dirname(__file__),
                                                'test-agent.yaml'))


class TestDynamicCheckHelper(unittest.TestCase):
    def setUp(self):
        agent_config = base_config.get_config(sections='Main')

        self._instances = [{'name': 'test',
                            'mapping': {
                                'gauges': ['stats.(MessagesAvg)'],
                                'counters': ['MessagesTotal'],
                                'dimensions': {
                                    'index': 'index',
                                    'simple_dimension': 'simple_label',
                                    'complex_dimension': {
                                        'source_key': 'complex_label',
                                        'regex': 'k8s_([._\-a-zA-Z0-9]*)_postfix'
                                    },
                                    'complex_dimension_rest': {
                                        'source_key': 'complex_label',
                                        'regex': 'k8s_([._\-a-zA-Z0-9]*_postfix)'
                                    }
                                },
                                'groups': {
                                    'testgroup': {
                                        'dimensions': {
                                            'user': 'user'
                                        },
                                        'rates': ['.*\.Responses.*', '(sec_auth_.*).stats',
                                                  '(io_service_bytes)_stats_Total']
                                    }
                                    # dimensions should be inherited from above
                                }}}]
        self.check = AgentCheck("DynCheckHelper-Teset", {}, agent_config, self._instances)  # TODO mock check
        self.helper = DynamicCheckHelper(self.check, 'dynhelper')

    def run_check(self):
        self.check.run()
        metric_dict = {"sec": {"auth": [{"user": "me", "total.stats": 10}, {"user": "you", "total.stats": 15}]},
                       "io_service_bytes": {"stats": {"Total": 10}}}
        self.helper.push_metric_dict(self._instances[0], metric_dict, group="testgroup",
                                     labels={'simple_label': 'simple_label_test',
                                             'complex_label': 'k8s_monasca-api-a8109321_postfix'}, max_depth=3)
        self.helper.push_metric(self._instances[0], metric='req.ResponsesOk', value=10.0,
                                group="testgroup",
                                labels={'simple_label': 'simple_label_test',
                                        'complex_label': 'k8s_monasca-api-a8109321_postfix'})
        self.helper.push_metric(self._instances[0], metric='stats.MessagesAvg', value=5.0,
                                labels={'simple_label': 'simple_label_test',
                                        'complex_label': 'k8s_monasca-api-a8109321_postfix'})
        self.helper.push_metric(self._instances[0], metric='MessagesTotal', value=1)
        time.sleep(1)
        self.helper.push_metric_dict(self._instances[0], metric_dict, group="testgroup",
                                     labels={'simple_label': 'simple_label_test',
                                             'complex_label': 'k8s_monasca-api-a8109321_postfix'}, max_depth=3)
        self.helper.push_metric(self._instances[0], metric='req.ResponsesOk', value=15.0,
                                group="testgroup",
                                labels={'simple_label': 'simple_label_test',
                                        'complex_label': 'k8s_monasca-api-a8109321_postfix'})
        self.helper.push_metric(self._instances[0], metric='MessagesTotal', value=100)
        metrics = self.check.get_metrics()

        return metrics

    def testMeasurements(self):
        metrics = self.run_check()
        for m in metrics:
            print("metric: {0}, dimensions: {1}".format(m['measurement']['name'], repr(m['measurement']['dimensions'])))

        def sortfilter(name):
            filterd = filter(lambda m: m['measurement']['name'] == name, metrics)
            return sorted(filterd, key=lambda m:m['measurement']['timestamp'])

        metric1 = sortfilter('dynhelper.messages_avg')
        metric2 = sortfilter('dynhelper.messages_total')
        metric3 = sortfilter('dynhelper.testgroup.req_responses_ok')
        metric4 = sortfilter('dynhelper.testgroup.sec_auth_total')
        self.assertTrue(len(metric1) > 0,
                        'gauge dynhelper.messages_avg missing in metric list {0}'.format(repr(metrics)))
        self.assertEqual(metric1[0]['measurement']['dimensions'],
                          {'simple_dimension': 'simple_label_test', 'complex_dimension': 'monasca-api-a8109321',
                           'complex_dimension_rest': 'monasca-api-a8109321_postfix',
                           'hostname': metric1[0]['measurement']['dimensions'].get('hostname')})
        self.assertTrue(len(metric2) > 0,
                        'rate dynhelper.messages_total missing in metric list {0}'.format(repr(metrics)))
        self.assertEqual(metric2[0]['measurement']['dimensions'],
                          {'hostname': metric2[0]['measurement']['dimensions'].get('hostname')})
        self.assertTrue(len(metric3) > 0,
                        'rate dynhelper.testgroup.req_responses_ok missing in metric list {0}'.format(repr(metrics)))
        self.assertEqual(metric3[0]['measurement']['dimensions'],
                          {'simple_dimension': 'simple_label_test', 'complex_dimension': 'monasca-api-a8109321',
                           'complex_dimension_rest': 'monasca-api-a8109321_postfix',
                           'hostname': metric3[0]['measurement']['dimensions'].get('hostname')})
        self.assertTrue(len(metric4) == 2,
                        'rate dynhelper.testgroup.sec_auth_total missing in metric list {0}'.format(repr(metrics)))
        self.assertEqual(metric4[0]['measurement']['dimensions'],
                          {'simple_dimension': 'simple_label_test', 'complex_dimension': 'monasca-api-a8109321',
                           'complex_dimension_rest': 'monasca-api-a8109321_postfix',
                           'user': 'me', 'hostname': metric4[0]['measurement']['dimensions'].get('hostname')})
        self.assertEqual(metric4[1]['measurement']['dimensions'],
                          {'simple_dimension': 'simple_label_test', 'complex_dimension': 'monasca-api-a8109321',
                           'complex_dimension_rest': 'monasca-api-a8109321_postfix',
                           'user': 'you', 'hostname': metric4[1]['measurement']['dimensions'].get('hostname')})
