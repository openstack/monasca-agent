# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import monasca_setup.detection


class Heat(monasca_setup.detection.ServicePlugin):

    """Detect Heat daemons and setup configuration to monitor them."""

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'orchestration',
            'process_names': ['heat-api ', 'heat-api-cfn',
                              'heat-api-cloudwatch', 'heat-engine'],
            'service_api_url': 'http://localhost:8004',
            'search_pattern': '.*versions.*',
        }

        super(Heat, self).__init__(service_params)
