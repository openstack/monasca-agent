import monasca_setup.detection


class Cinder(monasca_setup.detection.ServicePlugin):

    """Detect Cinder daemons and setup configuration to monitor them."""

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'block-storage',
            'process_names': ['cinder-volume', 'cinder-scheduler',
                              'cinder-api'],
            'service_api_url': 'http://localhost:8776/v2.0',
            'search_pattern': '.*version=1.*'
        }

        super(Cinder, self).__init__(service_params)
