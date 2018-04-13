# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development Company LP
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


class Neutron(monasca_setup.detection.ServicePlugin):

    """Detect Neutron daemons and setup configuration to monitor them.

    """

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'networking',
            'process_names': ['neutron-server', 'neutron-openvswitch-agent',
                              'neutron-rootwrap', 'neutron-dhcp-agent',
                              'neutron-vpn-agent', 'neutron-metadata-agent',
                              'neutron-metering-agent', 'neutron-l3-agent',
                              'bin/neutron-lbaas-agent',
                              'neutron-lbaasv2-agent',
                              'neutron-l2gateway-agent',
                              'infoblox-ipam-agent',
                              'ipsec/charon'],
            'service_api_url': 'http://localhost:9696',
            'search_pattern': '.*v2.0.*'
        }

        super(Neutron, self).__init__(service_params)

    def build_config(self):
        """Build the config as a Plugins object and return."""
        # Skip the http check if neutron-server is not on this box
        if 'neutron-server' not in self.found_processes:
            self.service_api_url = None
            self.search_pattern = None

        return monasca_setup.detection.ServicePlugin.build_config(self)
