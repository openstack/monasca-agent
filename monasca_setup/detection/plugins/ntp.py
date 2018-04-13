# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development LP
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
import os
import re

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)


class Ntp(monasca_setup.detection.Plugin):
    """Detect NTP daemon and setup configuration to monitor them.
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """
        if monasca_setup.detection.find_process_cmdline('ntpd') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        log.info("\tEnabling the ntp plugin")
        if os.path.exists('/etc/ntp.conf'):
            with open('/etc/ntp.conf', 'r') as ntp_config:
                ntp_conf = ntp_config.read()
            match = re.search('^server (.*?)( #|$)', ntp_conf, re.MULTILINE)
            if match is None:
                ntp_server = 'pool.ntp.org'
            else:
                # There can be additional options after the server hostname or IP Address
                server_val = match.group(1)
                ntp_server = server_val.split()[0]
        else:
            ntp_server = 'pool.ntp.org'
        if re.match('^127', ntp_server):
            log.warn(
                "NTP Server points to localhost no value in collecting NTP metrics."
                "Skipping configuration.")
            return None
        config['ntp'] = {'init_config': None, 'instances': [
            {'name': ntp_server, 'host': ntp_server}]}

        return config

    def dependencies_installed(self):
        try:
            import ntplib  # noqa
        except ImportError:
            return False
        else:
            return True
