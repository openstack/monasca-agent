# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import monasca_setup.detection


class Glance(monasca_setup.detection.ServicePlugin):

    """Detect Glance daemons and setup configuration to monitor them."""

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'image-service',
            'process_names': ['glance-registry',
                              'glance-api'],
            'service_api_url': 'http://localhost:9292',
            'search_pattern': '.*v2.0.*'
        }

        super(Glance, self).__init__(service_params)
