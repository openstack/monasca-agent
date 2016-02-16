# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging
import os

import yaml

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)


class PowerDNS(monasca_setup.detection.Plugin):

    """Detect PowerDNS daemon and setup configuration to monitor it.

    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        if monasca_setup.detection.find_process_cmdline('pdns_server') is not None:
            self.available = True

    def build_config(self):
        """Build the config and return.

        """
        log.info("\tWatching the pdns_server process.")
        return monasca_setup.detection.watch_process(
            ['pdns_server'], 'powerdns', exact_match=False)

    def dependencies_installed(self):
        return True
