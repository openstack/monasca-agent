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

from unittest import mock

from oslotest import base
import psutil

from monasca_setup.detection.plugins import zookeeper as zk

_DEFAULT_CFG_FILE = '/etc/zookeeper/conf/zoo.cfg'


def _get_cmd(config_file=_DEFAULT_CFG_FILE):
    return 'org.apache.zookeeper.server.quorum.QuorumPeerMain {0}'.format(config_file)


_ZOOKEEPER_CMD = _get_cmd()


class FakeProcess(object):
    cmdLine = None

    def as_dict(self, attrs=None):
        all_attrs = {'name': 'java',
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


class TestZookeeperDetection(base.BaseTestCase):

    FAKE_CONFIG_FILE_WITH_OPTIONS = ['tickTime=2000', 'initLimit=10',
                                     'syncLimit=5', 'dataDir=/var/lib/zookeeper',
                                     'clientPortAddress=192.168.10.6', 'clientPort=2182']

    FAKE_CONFIG_FILE_WITHOUT_OPTIONS = ['tickTime=2000', 'initLimit=10',
                                        'syncLimit=5', 'dataDir=/var/lib/zookeeper']

    BUILD_CONFIG = {'init_config': None,
                    'instances': [{'name': '192.168.10.6', 'host': '192.168.10.6',
                                   'port': 2181, 'timeout': 3}]}

    def setUp(self):
        super(TestZookeeperDetection, self).setUp()
        with mock.patch.object(zk.Zookeeper, '_detect') as mock_detect:
            self._zk = zk.Zookeeper('zookeeper')
            self.assertTrue(mock_detect.called)

    def test_should_not_configure_if_no_process(self):
        FakeProcess.cmdLine = []
        self._detect(proc=True)
        self.assertFalse(self._zk.available)

    def test_should_not_configure_has_process_no_config_located(self):
        FakeProcess.cmdLine = [_ZOOKEEPER_CMD]
        self._zk._get_config_file = mock.Mock(return_value=None)
        self._detect()
        self.assertFalse(self._zk.available)

    @mock.patch('monasca_setup.detection.plugins.zookeeper.os.path.isfile')
    def test_should_be_available_if_everything_matches(self, is_f):
        FakeProcess.cmdLine = [_ZOOKEEPER_CMD]
        is_f.return_value = True

        self._zk._get_config_file = mock.Mock(return_value=_DEFAULT_CFG_FILE)

        self._detect()
        self.assertTrue(self._zk.available)

    def test_should_detect_config_file_from_cmdline(self):
        FakeProcess.cmdLine = [_ZOOKEEPER_CMD]
        self.assertTrue(_DEFAULT_CFG_FILE, zk.Zookeeper._get_config_file(FakeProcess()))

    @mock.patch('monasca_setup.detection.plugins.zookeeper.os.path.isfile')
    def test_should_be_available_use_default_config_file(self, is_f):
        FakeProcess.cmdLine = [_get_cmd(config_file='')]
        is_f.return_value = True

        self._detect()
        self.assertTrue(self._zk.available)

    def test_should_return_default_config_file_if_in_cmdline_is_missing(self):
        FakeProcess.cmdLine = ['zookeeper']
        self.assertEqual('/etc/zookeeper/conf/zoo.cfg', zk.Zookeeper._get_config_file(FakeProcess()))

    @mock.patch('monasca_setup.detection.plugins.zookeeper.open')
    def test_should_return_options_from_config_file(self, open_file):
        open_file.return_value = self.FAKE_CONFIG_FILE_WITH_OPTIONS
        FakeProcess.cmdLine = []
        ip_address = '192.168.10.6'
        port = 2182
        self.assertEqual((ip_address, port), zk.Zookeeper._read_config_file(FakeProcess()))

    @mock.patch('monasca_setup.detection.plugins.zookeeper.open')
    def test_should_return_default_options_missing_in_config_file(self, open_file):
        open_file.return_value = self.FAKE_CONFIG_FILE_WITHOUT_OPTIONS
        FakeProcess.cmdLine = []
        ip_address = 'localhost'
        port = 2181
        self.assertEqual((ip_address, port), zk.Zookeeper._read_config_file(FakeProcess()))

    @mock.patch('monasca_setup.detection.plugins.zookeeper.open')
    def test_exception_while_parrsing_file(self, open_file):
        open_file.return_value = ['clientPort=aa']
        self.assertEqual(None, zk.Zookeeper._read_config_file(FakeProcess()))

    def test_should_build_config(self):
        config = ('192.168.10.6', 2181)
        FakeProcess.cmdLine = [_ZOOKEEPER_CMD]
        self._zk._get_config_file = mock.Mock(return_value=None)
        self._detect()
        self._zk._read_config_file = mock.Mock(return_value=config)
        self.assertEqual(self.BUILD_CONFIG, self._zk.build_config()['zk'])

    def _detect(self, proc=False):
        self._zk.available = False
        processes = [FakeProcess()] if not proc else []
        process_iter = mock.patch.object(psutil, 'process_iter',
                                         return_value=processes)
        with process_iter as mock_process_iter:
            self._zk._detect()
            self.assertTrue(mock_process_iter.called)
