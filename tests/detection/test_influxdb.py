# Copyright 2017 FUJITSU LIMITED
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

import mock

from oslotest import base
import psutil

from monasca_setup.detection.plugins import influxdb as idb

_DEFAULT_CFG_FILE = '/etc/influxdb/influxdb.conf'


def _get_cmd(config_file=_DEFAULT_CFG_FILE):
    """Builds mocked cmdline for process"""
    return ('/usr/bin/influxd -config %s' % config_file).split(' ')


_INFLUXDB_CMD = _get_cmd()


class FakeProcess(object):
    cmdLine = None

    def as_dict(self, attrs=None):
        all_attrs = {'name': 'influxd',
                     'exe': FakeProcess.exe(),
                     'cmdline': FakeProcess.cmdline()}
        if attrs:
            for key in attrs:
                if key not in all_attrs:
                    all_attrs.pop(key, None)
        return all_attrs

    @staticmethod
    def exe():
        line = FakeProcess.cmdLine
        if not line:
            return None
        return line[0]

    @staticmethod
    def cmdline():
        return FakeProcess.cmdLine


class TestInfluxDBDetection(base.BaseTestCase):
    ADDRESSES = {
        ':8086': ('127.0.0.1', 8086),
        '192.168.10.6:8888': ('192.168.10.6', 8888)
    }
    LOCATIONS = (
        '/tmp/influx.conf',
        _DEFAULT_CFG_FILE,
        '/etc/monasca/influx.conf'
    )

    def setUp(self):
        super(TestInfluxDBDetection, self).setUp()
        with mock.patch.object(idb.InfluxDB, '_detect') as mock_detect:
            self._ir = idb.InfluxDB('influxdb')
            self.assertTrue(mock_detect.called)

    def test_should_not_configure_if_no_process(self):
        FakeProcess.cmdLine = []  # no_process
        self._detect(no_proc=True)
        self.assertFalse(self._ir.available)

    def test_should_not_configure_has_process_no_config_located(self):
        FakeProcess.cmdLine = [_INFLUXDB_CMD]
        self._ir._get_config_file = mock.Mock(return_value=None)
        self._detect()
        self.assertFalse(self._ir.available)

    @mock.patch('monasca_setup.detection.plugins.influxdb.importutils')
    def test_should_not_configure_no_dependencies(self, iu):
        FakeProcess.cmdLine = [_INFLUXDB_CMD]
        self._ir._get_config_file = mock.Mock(return_value=True)
        iu.return_value = False
        self.assertFalse(self._ir.available)

    @mock.patch('monasca_setup.detection.plugins.influxdb.importutils')
    def test_should_be_available_if_everything_matches(self, iu):
        FakeProcess.cmdLine = [_INFLUXDB_CMD]

        self._ir._get_config_file = mock.Mock(return_value=_DEFAULT_CFG_FILE)
        self._ir._load_config = lc = mock.Mock()
        iu.try_import.return_value = True

        self._detect()

        self.assertTrue(self._ir.available)
        lc.assert_called_with(_DEFAULT_CFG_FILE)

    @mock.patch('monasca_setup.detection.plugins.influxdb.importutils')
    def test_dependencies_installed_true_has_toml(self, iu):
        iu.try_import = tr = mock.Mock(return_value=True)
        self.assertTrue(self._ir.dependencies_installed())
        tr.assert_called_with('toml', False)

    @mock.patch('monasca_setup.detection.plugins.influxdb.importutils')
    def test_dependencies_installed_false_no_toml(self, iu):
        iu.try_import = tr = mock.Mock(return_value=False)
        self.assertFalse(self._ir.dependencies_installed())
        tr.assert_called_with('toml', False)

    def test_should_explode_addresses(self):
        for raw_address, e_host_port in self.ADDRESSES.items():
            http_conf = {
                'bind-address': raw_address
            }
            a_host_port = idb.InfluxDB._explode_bind_address(http_conf)
            self.assertEqual(e_host_port, a_host_port)

    def test_should_return_none_cfg_file_if_cmd_switch_missing(self):
        FakeProcess.cmdLine = []
        self.assertIsNone(idb.InfluxDB._get_config_file(FakeProcess()))

    def test_should_return_cfg_file_path_if_cmd_switch_found(self):
        for loc in self.LOCATIONS:
            FakeProcess.cmdLine = _get_cmd(config_file=loc)
            self.assertEqual(loc,
                             idb.InfluxDB._get_config_file(FakeProcess()))

    @mock.patch('monasca_setup.detection.plugins.influxdb.'
                'utils.find_addrs_listening_on_port')
    def test_should_build_config_db_listens(self, falop):
        falop.return_value = True
        self._build_config(process_up=True)

    @mock.patch('monasca_setup.detection.plugins.influxdb.'
                'utils.find_addrs_listening_on_port')
    def test_should_build_config_db_died_during_conf(self, falop):
        falop.return_value = False
        self._build_config(process_up=False)

    @mock.patch('monasca_setup.detection.plugins.influxdb.'
                'utils.find_addrs_listening_on_port')
    def test_should_build_config_http_disabled(self, falop):
        falop.return_value = False
        self._build_config(http_enabled=False)

    @mock.patch('monasca_setup.detection.plugins.influxdb.'
                'utils.find_addrs_listening_on_port')
    def test_should_build_config_db_listens_with_influxdb_node_key(self, falop):
        falop.return_value = True
        self._ir.args = {'influxdb_node': 'test-key'}
        self._build_config(process_up=True)

    def _build_config(self, http_enabled=True, process_up=True):
        """Verify built configuration

        :param process_up: True/False, intermediate process availability
        :type process_up: bool
        :param http_enabled: Is http enabled for given influx
        :type http_enabled: bool

        """
        monitored_items = ['process']
        if process_up and http_enabled:
            monitored_items.append('http_check')

        for raw_address, host_port in self.ADDRESSES.items():
            self._ir._config = {
                'http': {
                    'enabled': http_enabled,
                    'bind-address': raw_address
                }
            }
            built_config = self._ir.build_config()

            self.assertItemsEqual(monitored_items, built_config.keys())
            for key in built_config.keys():
                if key == 'process':
                    self._verify_process_conf(built_config[key])
                elif key == 'http_check':
                    self._verify_http_conf(built_config[key], host_port)
                else:
                    raise 'Untested monitored item %s' % key

    def _verify_http_conf(self, built_config, e_host_port):
        dimensions = {
            'component': 'influxdb',
            'service': 'influxdb'
        }
        if self._ir.args and self._ir.args.get(self._ir.INFLUXDB_NODE_ARG_NAME):
            dimensions.update(
                {self._ir.INFLUXDB_NODE_ARG_NAME: self._ir.args.get(self._ir.INFLUXDB_NODE_ARG_NAME)})

        expected_http = {
            'init_config': None,
            'instances': [
                {
                    'name': 'influxdb',
                    'url': 'http://%s:%d/ping' % e_host_port,
                    'dimensions': dimensions
                }
            ]
        }
        self.assertDictEqual(expected_http, built_config)

    def _verify_process_conf(self, actual_config):
        dimensions = {
            'component': 'influxdb',
            'service': 'influxdb'
        }
        if self._ir.args and self._ir.args.get(self._ir.INFLUXDB_NODE_ARG_NAME):
            dimensions.update(
                {self._ir.INFLUXDB_NODE_ARG_NAME: self._ir.args.get(self._ir.INFLUXDB_NODE_ARG_NAME)})

        expected_process = {
            'init_config': None,
            'instances': [
                {
                    'detailed': True,
                    'search_string': ['influxd'],
                    'exact_match': False,
                    'name': 'influxd',
                    'dimensions': dimensions
                }
            ]
        }
        self.assertDictEqual(expected_process, actual_config)

    def _detect(self, no_proc=False):
        self._ir.available = False
        processes = [FakeProcess()] if not no_proc else []
        process_iter = mock.patch.object(psutil, 'process_iter',
                                         return_value=processes)
        with process_iter as mock_process_iter:
            self._ir._detect()
            self.assertTrue(mock_process_iter.called)
