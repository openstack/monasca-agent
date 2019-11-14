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

from datetime import datetime

from cryptography.hazmat.backends import default_backend
from cryptography import x509

from monasca_agent.collector.checks import AgentCheck


class CertificateFileCheck(AgentCheck):
    """Check the given certificate file and output a metric
       which is the number of days until it expires
    """

    def __init__(self, name, init_config, agent_config, instances=None):
        super(CertificateFileCheck, self).__init__(name, init_config,
                                                   agent_config, instances)

    def check(self, instance):
        cert_file = instance.get('cert_file', None)

        if cert_file is None:
            self.log.warning('Instance have no "cert_file" configured.')
            return

        dimensions = self._set_dimensions(None, instance)
        dimensions['cert_file'] = cert_file
        self.log.info('cert_file = %s' % cert_file)
        expire_in_days = self.get_expire_in_days(cert_file)
        if expire_in_days is not None:
            self.gauge('cert_file.cert_expire_days', expire_in_days,
                       dimensions=dimensions)
            self.log.debug('%d days till expiration for %s' % (expire_in_days,
                                                               cert_file))

    def get_expire_in_days(self, cert_file):
        """Take the path the the TLS certificate file and returns the number
           of till the certificate expires. If the certificate has already
           expired, it will return a negative number. For example,
           if the certificate has already expired 5 days prior to the check,
           -5 will be returned.
        """
        try:
            with open(cert_file, 'r') as cf:
                pem_data = cf.read().encode('ascii')

            cert = x509.load_pem_x509_certificate(pem_data, default_backend())
            return (cert.not_valid_after - datetime.utcnow()).days
        except IOError:
            self.log.warning(
                'Unable to read certificate from %s' % (cert_file))
        except ValueError:
            self.log.warning(
                'Unable to load certificate from %s. Invalid content.' % (
                    cert_file))
