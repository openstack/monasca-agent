import monasca_setup.detection

class Etcd(monasca_setup.detection.ServicePlugin):

    """Detect Etcd daemons and setup configuration to monitor them."""

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'etcd',
            'process_names': ['etcd'],
            # No healthcheck URL
            'service_api_url': '',
            'search_pattern': ''
        }

        super(Etcd, self).__init__(service_params)

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = super.build_config(self)
        log.info("\tEnabling the etcd plugin")
        config['etcd'] = {'init_config': None, 'instances': [{'url': 'http://localhost:2379'}]}

        return config
