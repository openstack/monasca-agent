# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import monasca_setup.detection


class Nova(monasca_setup.detection.ServicePlugin):

    """Detect Nova daemons and setup configuration to monitor them.

    """

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
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

        super(Nova, self).__init__(service_params)
