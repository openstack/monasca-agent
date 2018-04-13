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

import monasca_setup.detection


class Ovsvapp(monasca_setup.detection.ServicePlugin):

    """Detect OVSvApp service VM specific daemons and setup configuration to monitor them.

    """

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'OVSvApp-ServiceVM',
            'process_names': ['neutron-ovsvapp-agent', 'ovsdb-server', 'ovs-vswitchd'],
            'service_api_url': '',
            'search_pattern': ''
        }

        super(Ovsvapp, self).__init__(service_params)

    def build_config(self):
        """Build the config as a Plugins object and return."""
        self.service_api_url = None
        self.search_pattern = None

        return monasca_setup.detection.ServicePlugin.build_config(self)
