# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
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
import socket
import ssl

from six.moves.urllib.parse import urlparse

from monasca_agent.collector.checks import AgentCheck


class CertificateCheck(AgentCheck):
    """Uses ssl to get the SSL certificate and output a metric
       which is the number of days until it expires
    """

    def __init__(self, name, init_config, agent_config, instances=None):
        super(CertificateCheck, self).__init__(name, init_config,
                                               agent_config, instances)
        self._ca_certs = init_config.get('ca_certs')
        self._ciphers = init_config.get('ciphers')
        self._timeout = init_config.get('timeout')
        self.log.debug('ca_certs file is %s' % self._ca_certs)
        self.log.debug('cipers are %s' % self._ciphers)
        self.log.debug('timeout is %f' % self._timeout)

    def check(self, instance):
        url = instance.get('url', None)
        dimensions = self._set_dimensions(None, instance)
        dimensions['url'] = url
        self.log.info('url = %s' % url)
        try:
            expire_date = self.get_expire(url, self._ca_certs, self._ciphers,
                                          self._timeout)
            expire_in = expire_date - datetime.now()
            self.gauge('https.cert_expire_days', expire_in.days,
                       dimensions=dimensions)
            self.log.debug('%d days till expiration for %s' % (expire_in.days,
                                                               url))

        except Exception as e:
            self.log.warning('Exception trying to GET certificate for %s: %s' %
                             (url, e))
            self.log.exception('Failed to get certificate for %s' % url)

    def get_expire(self, url, ca_certs, ciphers, timeout):
        url_info = urlparse(url)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((url_info.hostname, url_info.port))
        ssl_sock = ssl.wrap_socket(sock, cert_reqs=ssl.CERT_REQUIRED,
                                   ca_certs=ca_certs,
                                   ciphers=(ciphers))

        cert = ssl_sock.getpeercert()

        not_after = cert['notAfter']
        try:
            expire_date = datetime.strptime(not_after,
                                            '%b %d %H:%M:%S %Y %Z')
            return expire_date
        except ValueError:
            raise Exception('Invalid Certificate date format')
