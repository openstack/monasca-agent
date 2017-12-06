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

import monasca_setup.agent_config
import monasca_setup.detection

_LXC_PWD = '/var/lib/lxc'
log = logging.getLogger(__name__)


class LXC(monasca_setup.detection.Plugin):
    """Detect if LXC is present on the host.

    LXC uses cgroup and namespaces to create a controlled and isolated
    environment. One can easily detect if lxc is installed on a machine,
    searching for /var/lib/lxc. But, if one uninstalls lxc, this dir must not
    be removed. THIS CAN NOT VERIFY ALL CONTAINERS (RUNNING AND STOPPED)
    WITHOUT ROOT ACCESS TO MONASCA-AGENT USER. Only running containers will be
    detected.

    To detect if any container is running, You can search if there are any
    folders in /sys/fs/cgroup/cpu/lxc/. Folders' names are the same as the
    running containers' names.
    """

    def __init__(self, template_dir, overwrite=True, args=None):
        self.service_name = 'lxc'
        super(LXC, self).__init__(template_dir, overwrite, args)

    def _detect(self):
        """Verify if there are container folder."""
        if os.path.exists(_LXC_PWD):
            self.available = True

    def build_config(self):
        config = monasca_setup.agent_config.Plugins()
        config['default'] = {'init_config': None,
                             'instances': [
                                 {'container': 'all',
                                  'state': True,
                                  'cpu': True,
                                  'mem': True,
                                  'blkio': True,
                                  'net': True
                                  }]}
        return config

    def dependencies_installed(self):
        return True
