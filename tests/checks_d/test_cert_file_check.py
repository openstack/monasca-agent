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

import datetime
import logging
import os
import shutil
import tempfile
from unittest import mock
import unittest

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import freezegun

from monasca_agent.collector.checks_d import cert_file_check

LOG = logging.getLogger('monasca_agent.collector.checks.check.cert_file_check')


def generate_selfsigned_cert(expired_in):
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=1024,
        backend=default_backend()
    )
    issuer = subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u'foo')
    ])
    now = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(issuer)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=expired_in))
        .sign(key, hashes.SHA256(), default_backend())
    )
    cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)

    return cert_pem.decode('ascii')


class TestCertificateFileCheck(unittest.TestCase):

    def setUp(self):
        super(TestCertificateFileCheck, self).setUp()
        self.cert_file_check_obj = cert_file_check.CertificateFileCheck(
            name='cert_file_check',
            init_config={},
            instances=[],
            agent_config={}
        )

    def test_cert_file_is_none(self):
        with mock.patch.object(LOG, 'warning') as mock_log:
            self.cert_file_check_obj.check({'foo': 'bar'})
            mock_log.assert_called_with(
                'Instance have no "cert_file" configured.')

    def test_unable_to_read_file(self):
        tmp_certdir = tempfile.mkdtemp(prefix='test-cert-file-check-')
        try:
            bogus_cert_file = os.path.join(tmp_certdir, 'foo')
            with mock.patch.object(LOG, 'warning') as mock_log:
                self.cert_file_check_obj.check({'cert_file': bogus_cert_file})
                mock_log.assert_called_with(
                    'Unable to read certificate from %s' % (bogus_cert_file))
        finally:
            shutil.rmtree(tmp_certdir)

    def test_unable_to_load_file(self):
        tmp_certdir = tempfile.mkdtemp(prefix='test-cert-file-check-')
        try:
            bogus_cert_file = os.path.join(tmp_certdir, 'foo')
            # create a non-PEM formatted certificate file
            with open(bogus_cert_file, 'w') as f:
                f.write('foo')

            with mock.patch.object(LOG, 'warning') as mock_log:
                self.cert_file_check_obj.check({'cert_file': bogus_cert_file})
                mock_log.assert_called_with(
                    'Unable to load certificate from %s. Invalid content.' % (
                        bogus_cert_file))
        finally:
            shutil.rmtree(tmp_certdir)

    def test_check(self):
        tmp_certdir = tempfile.mkdtemp(prefix='test-cert-file-check-')
        try:
            cert_file = os.path.join(tmp_certdir, 'foo')
            # create a self-signed cert that expires in 10 days from now
            with open(cert_file, 'w') as f:
                f.write(generate_selfsigned_cert(10))

            with mock.patch.object(cert_file_check.CertificateFileCheck,
                                   'gauge') as mock_gauge:
                self.cert_file_check_obj.check({'cert_file': cert_file})
                args, kwargs = mock_gauge.call_args
                # make sure the plugin correctly detect the given cert will be
                # expiring in equal or less than 10 days from now
                self.assertEqual('cert_file.cert_expire_days', args[0])
                self.assertLessEqual(args[1], 10)
        finally:
            shutil.rmtree(tmp_certdir)

    def test_check_expired_cert(self):
        tmp_certdir = tempfile.mkdtemp(prefix='test-cert-file-check-')
        try:
            cert_file = os.path.join(tmp_certdir, 'foo')
            # create a self-signed cert that has expired 10 days ago
            with open(cert_file, 'w') as f:
                f.write(generate_selfsigned_cert(10))

            now = datetime.datetime.utcnow()
            back_to_the_future = now + datetime.timedelta(days=20)
            with freezegun.freeze_time(back_to_the_future):
                with mock.patch.object(cert_file_check.CertificateFileCheck,
                                       'gauge') as mock_gauge:
                    self.cert_file_check_obj.check({'cert_file': cert_file})
                    args, kwargs = mock_gauge.call_args
                    # make sure the plugin correctly detect that the given
                    # cert has already expired
                    self.assertEqual('cert_file.cert_expire_days', args[0])
                    self.assertLessEqual(args[1], -9)
        finally:
            shutil.rmtree(tmp_certdir)
