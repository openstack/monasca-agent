# Copyright 2016 FUJITSU LIMITED
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

import os
import logging
from unittest import mock
import unittest
import json
import random

from monasca_agent.common import util
from monasca_agent.collector.checks_d import kibana

LOG = logging.getLogger(kibana.__name__)

_KIBANA_VERSION = '4.4.0'
_KIBANA_URL = 'http://localhost:5700/api/status'


class MockKibanaCheck(kibana.Kibana):
    def __init__(self):
        super(MockKibanaCheck, self).__init__(
            name='kibana',
            init_config={
                'url': _KIBANA_URL
            },
            instances=[],
            agent_config={}
        )


class KibanaCheckTest(unittest.TestCase):
    def setUp(self):
        super(KibanaCheckTest, self).setUp()
        with mock.patch.object(util, 'get_hostname'):
            self.kibana_check = MockKibanaCheck()
            self.kibana_check._get_kibana_version = mock.Mock(
                return_value=_KIBANA_VERSION
            )

    def test_should_throw_exception_if_url_not_specified(self):

        with self.assertRaises(Exception) as err:
            self.kibana_check.init_config = {}
            self.kibana_check.check(None)

        self.assertEqual('An url to kibana must be specified',
                         str(err.exception))

    def test_should_early_exit_if_all_metrics_disabled(self):
        with mock.patch.object(util, 'get_hostname') as _,\
                mock.patch.object(LOG, 'warning') as mock_log_warning:
            self.kibana_check._get_kibana_version = mock.Mock()
            self.kibana_check._get_data = mock.Mock()
            self.kibana_check._process_metrics = mock.Mock()

            self.kibana_check.check({'metrics': []})

            self.assertFalse(self.kibana_check._get_kibana_version.called)
            self.assertFalse(self.kibana_check._get_data.called)
            self.assertFalse(self.kibana_check._process_metrics.called)

            self.assertEqual(mock_log_warning.call_count, 1)
            self.assertEqual(mock_log_warning.call_args[0][0],
                             'All metrics have been disabled in configuration '
                             'file, nothing to do.')

    def test_failed_to_retrieve_data(self):
        with mock.patch.object(util, 'get_hostname') as _,\
                mock.patch.object(LOG, 'error') as mock_log_error,\
                mock.patch.object(LOG, 'exception') as mock_log_exception:
            exception = Exception('oh')
            self.kibana_check._get_data = mock.Mock(
                side_effect=exception)

            self.kibana_check.check({
                'metrics': ['heap_size',
                            'heap_used',
                            'load',
                            'req_sec',
                            'resp_time_avg',
                            'resp_time_max']
            })

            self.assertEqual(mock_log_error.call_count, 1)
            self.assertEqual(mock_log_error.call_args[0][0],
                             'Error while trying to get stats from Kibana[%s]'
                             % _KIBANA_URL)

            self.assertEqual(mock_log_exception.call_count, 1)
            self.assertEqual(mock_log_exception.call_args[0][0],
                             exception)

    def test_empty_data_returned(self):
        with mock.patch.object(util, 'get_hostname') as _, \
                mock.patch.object(LOG, 'warning') as mock_log_warning:
            self.kibana_check._get_data = mock.Mock(return_value=None)

            self.kibana_check.check({
                'metrics': ['heap_size',
                            'heap_used',
                            'load',
                            'req_sec',
                            'resp_time_avg',
                            'resp_time_max']
            })

            self.assertEqual(mock_log_warning.call_count, 1)
            self.assertEqual(mock_log_warning.call_args[0][0],
                             'No stats data was collected from kibana')

    def test_process_metrics(self):
        all_metrics = ['heap_size', 'heap_used', 'load',
                       'req_sec', 'resp_time_avg',
                       'resp_time_max']
        enabled_metrics = all_metrics[:random.randint(0, len(all_metrics) - 1)]

        if not enabled_metrics:
            # if random made a joke, make sure at least one metric
            # is there to check
            enabled_metrics.append(all_metrics[0])

        response = {
            'metrics': {
                'heapTotal': [],
                'heapUsed': [],
                'load': [],
                'requestsPerSecond': [],
                'responseTimeAvg': [],
                'responseTimeMax': [],
            }
        }

        with mock.patch.object(util, 'get_hostname'):
            self.kibana_check._get_data = mock.Mock(return_value=response)
            self.kibana_check._process_metric = mock.Mock()

            self.kibana_check.check({'metrics': enabled_metrics})

            self.assertTrue(self.kibana_check._process_metric.called)
            self.assertEqual(len(enabled_metrics),
                             self.kibana_check._process_metric.call_count)

    def test_check(self):
        fixture_file = os.path.dirname(
            os.path.abspath(__file__)) + '/fixtures/test_kibana.json'
        response = json.load(open(fixture_file))

        metrics = ['heap_size', 'heap_used', 'load',
                   'req_sec', 'resp_time_avg',
                   'resp_time_max']

        # expected value, see fixture values for details
        # it presents partial response kibana returns
        # mocked to always returned repeatable and known data

        # 96 values is in total
        # but 7 will be omitted because there not returned
        # in responseTimeAvg

        expected_metric = [
            'kibana.heap_size_mb',
            'kibana.heap_used_mb',
            'kibana.load_avg_1m',
            'kibana.load_avg_5m',
            'kibana.load_avg_15m',
            'kibana.req_sec',
            'kibana.resp_time_avg_ms',
            'kibana.resp_time_max_ms'
        ]

        with mock.patch.object(util, 'get_hostname'):
            self.kibana_check._get_data = mock.Mock(return_value=response)
            self.kibana_check.gauge = mock.Mock(return_value=response)

            self.kibana_check.check({'metrics': metrics})

            self.assertTrue(self.kibana_check.gauge.called)
            self.assertEqual(89, self.kibana_check.gauge.call_count)

            for call_arg in self.kibana_check.gauge.call_args_list:
                metric_name = call_arg[1]['metric']
                self.assertIn(metric_name, expected_metric)
