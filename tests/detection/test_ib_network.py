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


import monasca_setup.detection.plugins.ib_network as ib_network


class MockIBNetworkDetectPlugin(ib_network.IBNetworkDetect):
    def __init__(self):
        # Don't call the base class constructor
        pass


class TestIBNetworkDetect(unittest.TestCase):
    def setUp(self):
        self.ib_network = MockIBNetworkDetectPlugin()

    def test_build_config(self):
        config = self.ib_network.build_config()
        self.assertIn('ib_network', config)

    @mock.patch('os.path.isdir')
    def test__detect_ok(self, mock_isdir):
        mock_isdir.return_value = True
        self.ib_network._detect()
        mock_isdir.assert_called_once_with(ib_network._IB_DEVICE_PATH)
        self.assertTrue(self.ib_network.available)

    @mock.patch('os.path.isdir')
    def test__detect_no_infiniband(self, mock_isdir):
        mock_isdir.return_value = False
        self.ib_network._detect()
        mock_isdir.assert_called_once_with(ib_network._IB_DEVICE_PATH)
        self.assertFalse(self.ib_network.available)
