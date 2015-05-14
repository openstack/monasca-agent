import monasca_setup.detection


class Keystone(monasca_setup.detection.ServicePlugin):

    """Detect Keystone daemons and setup configuration to monitor them.

    """

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'identity-service',
            'process_names': ['keystone-'],
            'service_api_url': 'http://localhost:35357/v3',
            'search_pattern': '.*v3.0.*'
        }

        super(Keystone, self).__init__(service_params)
