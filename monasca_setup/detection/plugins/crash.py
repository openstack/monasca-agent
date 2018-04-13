# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

from monasca_setup import agent_config
from monasca_setup.detection import Plugin

log = logging.getLogger(__name__)


class Crash(Plugin):
    """Detect if kdump is installed and enabled and setup configuration to
       monitor for crash dumps.
    """

    def _detect(self):
        """Run detection, set self.available True if a crash kernel is loaded.
        """
        loaded = '/sys/kernel/kexec_crash_loaded'
        if os.path.isfile(loaded):
            with open(loaded, 'r') as fh:
                if fh.read().strip() == '1':
                    self.available = True

    def build_config(self):
        """Build the config as a Plugin object and return it.
        """
        log.info('\tEnabling the Monasca crash dump healthcheck')
        config = agent_config.Plugins()

        config['crash'] = {
            'init_config': None,
            'instances': [{'name': 'crash_stats'}]
        }

        return config

    def dependencies_installed(self):
        return True
