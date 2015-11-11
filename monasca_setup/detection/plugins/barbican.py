import monasca_setup.detection


class Barbican(monasca_setup.detection.ServicePlugin):

    """Detect Barbican daemons and setup configuration to monitor them."""

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'key-manager',
            'process_names': ['barbican-api'],
            'service_api_url': 'http://localhost:9311',
            'search_pattern': '.*v1.*'
        }

        super(Barbican, self).__init__(service_params)
