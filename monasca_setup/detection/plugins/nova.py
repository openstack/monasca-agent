import monasca_setup.detection


class Nova(monasca_setup.detection.ServicePlugin):

    """Detect Nova daemons and setup configuration to monitor them.

    """

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'compute',
            'process_names': ['nova-compute', 'nova-conductor',
                              'nova-cert', 'nova-network',
                              'nova-scheduler', 'nova-novncproxy',
                              'nova-xvpncproxy', 'nova-consoleauth',
                              'nova-objectstore', 'nova-api'],
            'service_api_url': 'http://localhost:8774/v2.0',
            'search_pattern': '.*version=2.*'
        }

        # Skip the http_check if disable_http_check is set
        if args is not None:
            args_dict = dict([a.split('=') for a in args.split()])
            if args_dict.get('disable_http_check', default=False):
                service_params['service_api_url'] = None
                service_params['self.search_pattern'] = None

        super(Nova, self).__init__(service_params)
