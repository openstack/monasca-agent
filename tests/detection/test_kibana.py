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

import logging
import os
from unittest import mock
import unittest
import psutil
import json
import six

from monasca_setup.detection.plugins import kibana

LOG = logging.getLogger(kibana.__name__)

_KIBANA_METRICS = ['heap_size',
                   'heap_used',
                   'load',
                   'req_sec',
                   'resp_time_avg',
                   'resp_time_max']


class JsonResponse(object):

    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


class PSUtilGetProc(object):
    cmdLine = ['kibana']

    def as_dict(self, attrs=None):
        return {'name': 'kibana',
                'cmdline': PSUtilGetProc.cmdLine}

    def cmdline(self):
        return self.cmdLine


class KibanaDetectionTest(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        with mock.patch.object(kibana.Kibana, '_detect') as mock_detect:
            self.kibana_plugin = kibana.Kibana('temp_dir')
            self.assertTrue(mock_detect.called)

    def _detect(self,
                kibana_plugin,
                config_is_file=True,
                deps_installed=True):
        kibana_plugin.available = False
        psutil_mock = PSUtilGetProc()

        with mock.patch.object(psutil, 'process_iter',
                               return_value=[psutil_mock]) as mock_process_iter, \
                mock.patch.object(os.path, 'isfile',
                                  return_value=config_is_file) as mock_isfile, \
                mock.patch.object(kibana_plugin,
                                  'dependencies_installed',
                                  return_value=deps_installed) as mock_deps_installed:
            kibana_plugin._detect()
            self.assertTrue(mock_process_iter.called)
            self.assertTrue(mock_isfile.called)
            self.assertTrue(mock_deps_installed.called)

    def _verify_kibana_conf(self, kibana_check, kibana_url):

        self.assertIn('init_config', kibana_check)
        self.assertIsNotNone(kibana_check['init_config'])
        self.assertIn('url', kibana_check['init_config'])
        self.assertEqual(kibana_check['init_config']['url'], kibana_url)

        self.assertIn('instances', kibana_check)
        self.assertEqual(1, len(kibana_check['instances']))

        for instance in kibana_check['instances']:
            self.assertIn('metrics', instance)
            self.assertEqual(list, type(instance['metrics']))
            six.assertCountEqual(self, _KIBANA_METRICS, instance['metrics'])

    def _verify_process_conf(self, process_check, kibana_user):
        # minimize check here, do not check how process should work
        # just find the user

        self.assertIn('instances', process_check)
        self.assertEqual(1, len(process_check['instances']))

        for instance in process_check['instances']:
            if not kibana_user:
                self.assertNotIn('username', instance)
            else:
                self.assertIn('username', instance)
                self.assertEqual(kibana_user, instance['username'])

    def test_no_detect_no_process(self):
        with mock.patch.object(LOG, 'info') as mock_log_info:
            PSUtilGetProc.cmdLine = []
            self._detect(self.kibana_plugin)
            self.assertFalse(self.kibana_plugin.available)

            self.assertEqual(mock_log_info.call_count, 1)
            self.assertEqual(mock_log_info.call_args[0][0],
                             'Kibana process has not been found. '
                             'Plugin for Kibana will not be configured.')

    def test_no_detect_no_dependencies(self):
        with mock.patch.object(LOG, 'error') as mock_log_error:
            self._detect(self.kibana_plugin, deps_installed=False)
            self.assertFalse(self.kibana_plugin.available)

            self.assertEqual(mock_log_error.call_count, 1)
            self.assertEqual(mock_log_error.call_args[0][0],
                             'Kibana plugin dependencies are not satisfied. '
                             'Module "pyaml" not found. '
                             'Plugin for Kibana will not be configured.')

    def test_no_detect_no_default_config_file(self):
        with mock.patch.object(LOG, 'warning') as mock_log_warning:
            self._detect(self.kibana_plugin, config_is_file=False)
            self.assertFalse(self.kibana_plugin.available)

            self.assertEqual(mock_log_warning.call_count, 1)
            self.assertEqual(mock_log_warning.call_args[0][0],
                             'Kibana plugin cannot find configuration '
                             'file /opt/kibana/config/kibana.yml. '
                             'Plugin for Kibana will not be configured.')

    def test_no_detect_no_args_config_file(self):
        config_file = '/fake/config'

        patch_log_warning = mock.patch.object(LOG, 'warning')

        with patch_log_warning as mock_log_warning:
            self.kibana_plugin.args = {'kibana-config': config_file}

            self._detect(self.kibana_plugin, config_is_file=False)
            self.assertFalse(self.kibana_plugin.available)

            self.assertEqual(mock_log_warning.call_count, 1)
            self.assertEqual(mock_log_warning.call_args[0][0],
                             'Kibana plugin cannot find configuration '
                             'file %s. '
                             'Plugin for Kibana will not be configured.'
                             % config_file)

    def test_detect_ok(self):
        self._detect(self.kibana_plugin)
        self.assertTrue(self.kibana_plugin.available)

    def test_build_config_unreadable_config(self):
        with mock.patch.object(LOG, 'error') as mock_log_error, \
                mock.patch.object(LOG, 'exception') as mock_log_exception, \
                mock.patch.object(self.kibana_plugin,
                                  '_read_config',
                                  side_effect=Exception('oh')) as _:
            self.kibana_plugin.build_config()

            self.assertEqual(mock_log_error.call_count, 1)
            self.assertEqual(mock_log_error.call_args[0][0],
                             'Failed to read configuration at '
                             '/opt/kibana/config/kibana.yml')

            self.assertEqual(mock_log_exception.call_count, 1)
            self.assertEqual(repr(mock_log_exception.call_args[0][0]),
                             repr(Exception('oh')))

    def test_build_config_https_support(self):
        config = ('localhost', 5700, 'https')

        with mock.patch.object(LOG, 'error') as mock_log_error, \
                mock.patch.object(self.kibana_plugin,
                                  '_read_config',
                                  return_value=config) as _:
            self.assertIsNone(self.kibana_plugin.build_config())

            self.assertEqual(mock_log_error.call_count, 1)
            self.assertEqual(mock_log_error.call_args[0][0],
                             '"https" protocol is currently not supported')

    def test_build_config_no_metric_support(self):
        config = ('localhost', 5700, 'http')

        with mock.patch.object(LOG, 'warning') as patch_log_warning,\
                mock.patch.object(self.kibana_plugin,
                                  '_read_config',
                                  return_value=config) as _,\
                mock.patch.object(self.kibana_plugin,
                                  '_has_metrics_support',
                                  return_value=False) as __:
            self.assertIsNone(self.kibana_plugin.build_config())

            self.assertEqual(patch_log_warning.call_count, 1)
            self.assertEqual(patch_log_warning.call_args[0][0],
                             'Running kibana does not support '
                             'metrics, skipping...')

    def test_build_config_ok_no_kibana_user(self):
        self._test_build_config_ok(None)

    def test_build_config_ok_kibana_user(self):
        self._test_build_config_ok('kibana-wizard')

    def _test_build_config_ok(self, kibana_user):
        kibana_host = 'localhost'
        kibana_port = 5700
        kibana_protocol = 'http'

        kibana_cfg = (kibana_host, kibana_port, kibana_protocol)
        kibana_url = '%s://%s:%d/api/status' % (
            kibana_protocol,
            kibana_host,
            kibana_port
        )

        fixture_file = (os.path.dirname(os.path.abspath(__file__))
                        + '/../checks_d/fixtures/test_kibana.json')
        response = json.load(open(fixture_file))

        get_metric_req_ret = mock.Mock(
            wraps=JsonResponse(response)
        )

        self.kibana_plugin.args = {'kibana-user': kibana_user}

        with mock.patch.object(self.kibana_plugin,
                               '_read_config',
                               return_value=kibana_cfg) as patch_read_config,\
                mock.patch.object(self.kibana_plugin,
                                  '_has_metrics_support',
                                  return_value=True) as has_metrics_patch,\
                mock.patch.object(self.kibana_plugin,
                                  '_get_metrics_request',
                                  return_value=get_metric_req_ret) as get_metrics_patch:
            conf = self.kibana_plugin.build_config()
            self.assertIsNotNone(conf)

            six.assertCountEqual(self, ['kibana', 'process'], conf.keys())
            self._verify_kibana_conf(conf['kibana'], kibana_url)
            self._verify_process_conf(conf['process'], kibana_user)
