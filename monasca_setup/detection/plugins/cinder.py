# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import monasca_setup.detection


class Cinder(monasca_setup.detection.ServicePlugin):

    """Detect Cinder daemons and setup configuration to monitor them."""

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'block-storage',
            'process_names': ['cinder-scheduler',
                              'cinder-api'],
            'service_api_url': 'http://localhost:8776/v2',
            'search_pattern': '.*version=1.*'
        }
        # process_names: cinder-volume and cinder-backup can
        # migrate legitimately so monitor those selectively
        # elsewhere

        super(Cinder, self).__init__(service_params)
