# Copyright 2019 SUSE LLC
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
import unittest

from mock import patch

from monasca_setup.detection.plugins.cert_file_check import CertificateFileCheck

LOG = logging.getLogger('monasca_setup.detection.plugins.cert_check')


class TestCertFileCheck(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        with patch.object(CertificateFileCheck, '_detect') as mock_detect:
            self.cert_obj = CertificateFileCheck('temp_dir')
            self.assertTrue(mock_detect.called)
            self.cert_obj.args = {'cert_files': '/etc/myservice/myserver.pem'}

    def test_detect(self):
        self.cert_obj.available = False
        with patch.object(self.cert_obj, '_check_required_args',
                          return_value=True) as mock_check_required_args:
            self.cert_obj._detect()
            self.assertTrue(self.cert_obj.available)
            self.assertTrue(mock_check_required_args.called)

    def _build_config(self):
        with patch.object(self.cert_obj, '_build_instance',
                          return_value={}) as mock_build_instance:
            result = self.cert_obj.build_config()
            self.assertTrue(mock_build_instance.called)
            self.assertEqual(
                result['cert_file_check']['instances'][0]['cert_file'],
                '/etc/myservice/myserver.pem')
            self.assertEqual(result['cert_file_check']['instances'][0]['name'],
                             '/etc/myservice/myserver.pem')
            return result

    def test_build_config_without_args(self):
        result = self._build_config()
        self.assertEqual(
            result['cert_file_check']['init_config']['collect_period'],
            3600)

    def test_build_config_with_args(self):
        self.cert_obj.args.update({'collect_period': 1200})
        result = self._build_config()
        self.assertEqual(
            result['cert_file_check']['init_config']['collect_period'],
            1200)
