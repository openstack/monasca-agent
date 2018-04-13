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
import unittest

from mock import patch

from monasca_setup.detection.plugins.cert_check import CertificateCheck

LOG = logging.getLogger('monasca_setup.detection.plugins.cert_check')


class TestCertCheck(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        with patch.object(CertificateCheck, '_detect') as mock_detect:
            self.cert_obj = CertificateCheck('temp_dir')
            self.assertTrue(mock_detect.called)
            self.cert_obj.args = {'urls': 'http://fake-cert.com'}

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
            self.assertEqual(result['cert_check']['instances'][0]['url'],
                             'http://fake-cert.com')
            self.assertEqual(result['cert_check']['instances'][0]['name'],
                             'http://fake-cert.com')
            return result

    def test_build_config_without_args(self):
        result = self._build_config()
        self.assertEqual(result['cert_check']['init_config']['ca_certs'],
                         '/etc/ssl/certs/ca-certificates.crt')
        self.assertEqual(result['cert_check']['init_config']['ciphers'],
                         'HIGH:-aNULL:-eNULL:-PSK:RC4-SHA:RC4-MD5')
        self.assertEqual(result['cert_check']['init_config']['collect_period'],
                         3600)
        self.assertEqual(result['cert_check']['init_config']['timeout'],
                         1.0)

    def test_build_config_with_args(self):
        self.cert_obj.args.update({'ca_certs': '/tmp/ssl/certs/ca-certificates.crt',
                                   'ciphers': 'fake-cipher',
                                   'timeout': 3.0,
                                   'collect_period': 1200})
        result = self._build_config()
        self.assertEqual(result['cert_check']['init_config']['ca_certs'],
                         '/tmp/ssl/certs/ca-certificates.crt')
        self.assertEqual(result['cert_check']['init_config']['ciphers'],
                         'fake-cipher')
        self.assertEqual(result['cert_check']['init_config']['collect_period'],
                         1200)
        self.assertEqual(result['cert_check']['init_config']['timeout'],
                         3.0)

    def test_timeout_error_log(self):
        self.cert_obj.args.update({'ca_certs': '/tmp/ssl/certs/ca-certificates.crt',
                                   'ciphers': 'fake-cipher',
                                   'timeout': 0.0,
                                   'collect_period': 1200})
        with patch.object(LOG, 'error') as mock_log:
            result = self._build_config()
            self.assertEqual(result['cert_check']['init_config']['ca_certs'],
                             '/tmp/ssl/certs/ca-certificates.crt')
            self.assertEqual(result['cert_check']['init_config']['ciphers'],
                             'fake-cipher')
            self.assertEqual(result['cert_check']['init_config']['collect_period'],
                             1200)
            self.assertEqual(result['cert_check']['init_config']['timeout'],
                             1.0)
            self.assertTrue(mock_log.called)
