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

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)

DEFAULT_COLLECT_PERIOD = 3600


class CertificateFileCheck(monasca_setup.detection.ArgsPlugin):
    """Setup a X.509 certificate file check according to the passed in args.

       Outputs one metric: cert_file.cert_expire_days which is the number of
       days until the certificate expires

       Despite being a detection plugin, this plugin does no detection and
       will be a NOOP without arguments.  Expects one argument, 'cert_files'
       which is a comma-separated list of PEM-formatted X.509 certificate
       files.

       Examples:

       monasca-setup -d CertificateFileCheck -a "cert_files=cert1.pem,cert2.pem"

       These arguments are optional:
       collect_period: Integer time in seconds between outputting the metric.
                       Since the metric is in days, it makes sense to output
                       it at a slower rate. The default is once per hour
    """

    def _detect(self):
        """Run detection, set self.available True if cert_files are detected
        """
        self.available = self._check_required_args(['cert_files'])

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        instances = []
        init_config = {'collect_period': DEFAULT_COLLECT_PERIOD}
        if 'collect_period' in self.args:
            collect_period = int(self.args['collect_period'])
            init_config['collect_period'] = collect_period
        for cert_file in self.args['cert_files'].split(','):
            cert_file = cert_file.strip()
            # Allow comma terminated lists
            if not cert_file:
                continue
            log.info("\tAdding X.509 Certificate expiration check for {}".format(cert_file))
            instance = self._build_instance([])
            instance.update({'cert_file': cert_file, 'name': cert_file})
            instances.append(instance)

        config['cert_file_check'] = {'init_config': init_config,
                                     'instances': instances}

        return config
