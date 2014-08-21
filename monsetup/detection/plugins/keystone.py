import monsetup.detection


class Keystone(monsetup.detection.ServicePlugin):

    """Detect Keystone daemons and setup configuration to monitor them.

    """

    def __init__(self, template_dir, overwrite=True):
        service_params = {
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'keystone',
            'process_names': ['keystone-all'],
            'service_api_url': 'http://localhost:35357/v3',
            'search_pattern': '.*v3.0.*'
        }

        super(Keystone, self).__init__(service_params)
