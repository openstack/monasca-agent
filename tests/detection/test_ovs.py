# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP
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
import psutil
import re
import unittest

from oslo_config import cfg

from mock import patch
from mock.mock import MagicMock
from six.moves import configparser

from monasca_setup.detection import utils
from monasca_setup.detection.plugins.ovs import Ovs


LOG = logging.getLogger('monasca_setup.detection.plugins.ovs')


class ps_util_get_proc:
    cmdLine = ['/etc/neutron/neutron.conf']
    detect_warning = False
    def as_dict(self, attrs=None):
        return {'name': 'neutron-openvsw',
                'cmdline': self.cmdline()}

    def cmdline(self):
        if not ps_util_get_proc.detect_warning:
            return ['neutron-openvsw',
                    ps_util_get_proc.cmdLine[0]]
        else:
            return ['/opt/fake.txt']


class TestOvs(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        with patch.object(Ovs, '_detect') as mock_detect:
            self.ovs_obj = Ovs('temp_dir')
            self.has_option = [True, False, True, False, False, True]
            self.get_value = [MagicMock(), MagicMock(), MagicMock(),
                              MagicMock(), MagicMock(), 'http://10.10.10.10',
                              'region1']
            self.assertTrue(mock_detect.called)

    def _detect(self, ovs_obj, file_config_valid=True):
        ovs_obj.neutron_conf = None
        ovs_obj.available = False

        with patch.object(cfg, 'CONF') as mock_conf, \
                patch.object(psutil, 'process_iter',
                             return_value=[ps_util_get_proc()]) \
                        as mock_process_iter, \
                patch.object(os.path, 'isfile', return_value=True) \
                        as mock_isfile,\
                patch.object(ovs_obj, 'dependencies_installed', return_value=True) \
                        as dependencies,\
                patch.object(ovs_obj, '_is_neutron_conf_valid',
                             return_value=file_config_valid) as _:
            ovs_obj._detect()
            self.assertTrue(mock_process_iter.called)
            if not ps_util_get_proc.cmdLine:
                self.assertFalse(mock_isfile.called)

    def _build_config(self, ovs_obj, dependencies_installed=True):
        ovs_obj.conf = MagicMock()
        ovs_obj.conf.default_config_files = ovs_obj.neutron_conf
        ovs_obj.conf.default_config_dirs = os.path.abspath(os.path.join(ovs_obj.neutron_conf, os.pardir))
        with patch.object(configparser, 'SafeConfigParser') as mock_config_parser:
            config_parser_obj = mock_config_parser.return_value

            with patch.object(cfg, 'CONF') as mock_conf, \
                    patch.object(LOG, 'info') as mock_log_info,\
                    patch.object(ovs_obj, 'has_option',
                                 side_effect=self.has_option) as mock_has_option, \
                    patch.object(ovs_obj, 'get_option',
                                 side_effect=self.get_value) as mock_get:
                result = ovs_obj.build_config()
                if dependencies_installed:
                    self.assertTrue(mock_log_info.called)
                    self.assertTrue(mock_has_option.called)
                    self.assertTrue(mock_get.called)
                    if not self.has_option[-1]:
                        self.assertIn(str(('nova', 'region_name')),
                                      str(mock_get.call_args_list[-1]))
                    else:
                        self.assertIn(str(('service_auth', 'region')),
                                      str(mock_get.call_args_list[-1]))
                return result

    def _build_config_with_arg(self, ovs_obj):
            result = self._build_config(ovs_obj)
            self.assertEqual(result['ovs']['init_config']['neutron_refresh'],
                             13000)
            self.assertFalse(result['ovs']['init_config']['network_use_bits'])
            self.assertIsInstance(result['ovs']['init_config']['username'],
                                  MagicMock)
            self.assertIsInstance(result['ovs']['init_config']['password'],
                                  MagicMock)
            self.assertIsInstance(result['ovs']['init_config']['project_name'],
                                  MagicMock)
            self.assertEqual(result['ovs']['init_config']['auth_url'],
                             'http://10.10.10.10')
            self.assertEqual(result['ovs']['init_config']['region_name'],
                             'region1')
            self.assertEqual(result['ovs']['init_config']['cache_dir'],
                             "/dev/shm")
            self.assertEqual(result['ovs']['init_config']['ovs_cmd'],
                             "sudo /usr/bin/ovs-vsctl")
            self.assertFalse(result['ovs']['init_config']['use_absolute_metrics'])
            self.assertTrue(result['ovs']['init_config']['use_rate_metrics'])
            self.assertTrue(result['ovs']['init_config']['use_health_metrics'])
            return result

    def _build_config_without_args(self, ovs_obj):
        result = self._build_config(ovs_obj)
        self.assertEqual(result['ovs']['init_config']['neutron_refresh'],
                         14400)
        self.assertFalse(result['ovs']['init_config']['network_use_bits'])
        self.assertEqual(result['ovs']['init_config']['cache_dir'],
                         "/dev/shm")
        self.assertEqual(result['ovs']['init_config']['ovs_cmd'],
                         "sudo /usr/bin/ovs-vsctl")
        self.assertEqual(result['ovs']['init_config']['included_interface_re'],
                         'qg.*|vhu.*|sg.*')
        self.assertIsInstance(result['ovs']['init_config']['username'],
                              MagicMock)
        self.assertIsInstance(result['ovs']['init_config']['password'],
                              MagicMock)
        self.assertIsInstance(result['ovs']['init_config']['project_name'],
                              MagicMock)
        self.assertTrue(result['ovs']['init_config']['use_absolute_metrics'])
        self.assertTrue(result['ovs']['init_config']['use_rate_metrics'])
        self.assertTrue(result['ovs']['init_config']['use_health_metrics'])
        return result

    def test_detect(self):
        with patch.object(utils, 'load_oslo_configuration'):
            self._detect(self.ovs_obj)
            self.assertTrue(self.ovs_obj.available)
            self.assertEqual(self.ovs_obj.neutron_conf,
                             '/etc/neutron/neutron.conf')

    def test_detect_invalid_config_file(self):
        self._detect(self.ovs_obj, file_config_valid=False)
        self.assertFalse(self.ovs_obj.available)
        self.assertIsNone(self.ovs_obj.neutron_conf)

    def test_detect_devstack(self):
        ps_util_get_proc.cmdLine = ['--config-file=/opt/stack/neutron.conf']
        with patch.object(utils, 'load_oslo_configuration'):
            self._detect(self.ovs_obj)
            self.assertTrue(self.ovs_obj.available)
            self.assertEqual(self.ovs_obj.neutron_conf, '/opt/stack/neutron.conf')

    def test_detect_info(self):
        with patch.object(LOG, 'info') as mock_log_warn:
            ps_util_get_proc.detect_warning = True
            self._detect(self.ovs_obj)
            self.assertFalse(self.ovs_obj.available)
            self.assertIsNone(self.ovs_obj.neutron_conf)
            self.assertTrue(mock_log_warn.called)

    def test_detect_conf_file_path_given(self):
        self.ovs_obj.neutron_conf = None
        self.ovs_obj.args = {'conf_file_path': '/opt/stack/neutron.conf'}

        with patch.object(utils, 'load_oslo_configuration') as mock_conf, \
                patch.object(psutil, 'process_iter',
                             return_value=[ps_util_get_proc()]) as mock_process_iter, \
                patch.object(os.path, 'isfile', return_value=True) as mock_isfile, \
                patch.object(self.ovs_obj, 'dependencies_installed',
                             return_value=True) as dependencies, \
                patch.object(self.ovs_obj, '_is_neutron_conf_valid',
                             return_value=True) as _:
            self.ovs_obj._detect()
            self.assertTrue(mock_isfile.called)
            self.assertTrue(self.ovs_obj.available)
            self.assertEqual(self.ovs_obj.neutron_conf,
                             '/opt/stack/neutron.conf')

    def test_build_config(self):
        self.ovs_obj.neutron_conf = 'neutron-conf'
        self._build_config_without_args(self.ovs_obj)

    def test_build_config_with_args(self):
        with patch.object(LOG, 'warn') as mock_log_warn:
            self.ovs_obj.neutron_conf = 'neutron-conf'
            self.ovs_obj.args = {'username': 'admin',
                                 'password': 'password',
                                 'project_name': 'tenant',
                                 'auth_url': '10.10.10.20',
                                 'region_name': 'region0',
                                 'neutron_refresh': 13000,
                                 'use_absolute_metrics': False}
            result = self._build_config_with_arg(self.ovs_obj)
            self.assertTrue(mock_log_warn.called)
            self.assertEqual(mock_log_warn.call_count, 5)
            self.assertEqual(result['ovs']['init_config']['included_interface_re'],
                             'qg.*|vhu.*|sg.*')

    def test_dependencies_not_installed(self):
        result = self.ovs_obj.dependencies_installed()
        self.assertEqual(result, False)

    def test_build_config_invalid_arg_warning(self):
        with patch.object(LOG, 'warn') as mock_log_warn:
            self.ovs_obj.neutron_conf = 'neutron-conf'
            self.ovs_obj.args = {'username': 'admin',
                                 'password': 'password',
                                 'project_name': 'tenant',
                                 'user_domain_name': 'default',
                                 'project_domain_name': 'default',
                                 'auth_url': '10.10.10.20',
                                 'region_name': 'region0',
                                 'neutron_refresh': 13000,
                                 'use_absolute_metrics': False,
                                 'invalid_arg': 'inv-arg'}
            result = self._build_config_with_arg(self.ovs_obj)
            self.assertTrue(mock_log_warn.called)
            self.assertEqual(mock_log_warn.call_count, 8)
            self.assertEqual(result['ovs']['init_config']['included_interface_re'],
                             'qg.*|vhu.*|sg.*')

    def test_build_config_if_auth_version(self):
        self.ovs_obj.neutron_conf = 'neutron-conf'
        self.has_option = [True, False, True, False, True, True]
        self.get_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock(),
                          MagicMock(), 'http://10.10.10.10',
                          'http://10.10.10.10', 'region1']
        result = self._build_config_without_args(self.ovs_obj)
        self.assertEqual(result['ovs']['init_config']['auth_url'],
                         'http://10.10.10.10')

    def test_build_config_if_auth_url_has_version(self):
        self.ovs_obj.neutron_conf = 'neutron-conf'
        self.has_option = [True, False, True, False, True, True]
        self.get_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock(),
                          MagicMock(), 'http://10.10.10.10/v1',
                          'http://10.10.10.10/v1', 'region1']
        result = self._build_config_without_args(self.ovs_obj)
        self.assertEqual(result['ovs']['init_config']['auth_url'],
                         'http://10.10.10.10/v1')

    def test_build_config_region_name_from_nova(self):
        self.ovs_obj.neutron_conf = 'neutron-conf'
        self.has_option = [True, False, True, False, False, False]
        self.get_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock(),
                          MagicMock(), 'http://10.10.10.10', 'region2']
        result = self._build_config_without_args(self.ovs_obj)
        self.assertEqual(result['ovs']['init_config']['auth_url'],
                         'http://10.10.10.10')
        self.assertEqual(result['ovs']['init_config']['region_name'],
                         'region2')

    def test_build_config_with_valid_interface_re(self):
        self.ovs_obj.neutron_conf = 'neutron-conf'
        self.ovs_obj.args = {'included_interface_re': 'tap.*',
                             'neutron_refresh': 13000,
                             'use_absolute_metrics': False}
        result = self._build_config_with_arg(self.ovs_obj)
        self.assertEqual(result['ovs']['init_config']['included_interface_re'],
                         'tap.*')

    def test_build_config_with_invalid_interface_re(self):
        self.ovs_obj.neutron_conf = 'neutron-conf'
        self.ovs_obj.args = {'included_interface_re': '[',
                             'neutron_refresh': 13000}

        with patch.object(re, 'compile', side_effect=re.error('error')) as mock_re_error, \
                patch.object(LOG, 'exception') as mock_log:
            self.assertRaises(Exception, self._build_config_with_arg, self.ovs_obj)
            self.assertTrue(mock_re_error.called)
            self.assertTrue(mock_log.called)
