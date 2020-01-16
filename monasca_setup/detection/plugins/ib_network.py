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

import logging
import os

import monasca_setup.agent_config
import monasca_setup.detection

LOG = logging.getLogger(__name__)

_IB_DEVICE_PATH = "/sys/class/infiniband/"


class IBNetworkDetect(monasca_setup.detection.Plugin):
    """Detects and configures Infiniband plugin."""
    def _detect(self):
        self.available = False
        if not self._detect_infiniband():
            LOG.info('Infiniband hardware was not detected: ib_network plugin'
                     'will not be loaded.')
            return
        self.available = True

    def build_config(self):
        config = monasca_setup.agent_config.Plugins()
        config['ib_network'] = {'init_config': None,
                                'instances': [{'name': 'ib_network_stats'}]}
        return config

    def _detect_infiniband(self):
        return os.path.isdir(_IB_DEVICE_PATH)
