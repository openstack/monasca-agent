import monsetup.detection


class Glance(monsetup.detection.ServicePlugin):

    """Detect Glance daemons and setup configuration to monitor them."""

    def __init__(self, template_dir, overwrite=True):
        service_params = {
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'glance',
            'process_names': ['glance-registry',
                              'glance-api'],
            'service_api_url': 'http://localhost:9292',
            'search_pattern': '.*v2.0.*'
        }

        super(Glance, self).__init__(service_params)
