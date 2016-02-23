# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

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
