import monasca_setup.detection


class Neutron(monasca_setup.detection.ServicePlugin):

    """Detect Neutron daemons and setup configuration to monitor them.

    """

    def __init__(self, template_dir, overwrite=True):
        service_params = {
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'networking',
            'process_names': ['neutron-server', 'neutron-openvswitch-agent',
                              'neutron-rootwrap', 'neutron-dhcp-agent',
                              'neutron-vpn-agent', 'neutron-metadata-agent',
                              'neutron-metering-agent', 'neutron-ns-metadata-proxy'],
            'service_api_url': 'http://localhost:9696',
            'search_pattern': '.*v2.0.*'
        }

        super(Neutron, self).__init__(service_params)
