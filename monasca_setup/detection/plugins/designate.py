import monasca_setup.detection


class Designate(monasca_setup.detection.ServicePlugin):

    """Detect Designate daemons and setup configuration to monitor them.

    """

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'dns',
            'process_names': ['designate-api',
                              'designate-central',
                              'designate-mdns',
                              'designate-pool-manager',
                              'designate-zone-manager',
                              'designate-sink',
                              'designate-agent'],
            'service_api_url': 'http://localhost:9001',
            'search_pattern': '.*200 OK.*',
        }

        super(Designate, self).__init__(service_params)
