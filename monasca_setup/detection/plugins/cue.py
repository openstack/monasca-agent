# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import monasca_setup.detection


class Cue(monasca_setup.detection.ServicePlugin):

    """Detect Cue daemons and setup configuration to monitor them."""

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'message-broker',
            'process_names': ['cue-api', 'cue-worker', 'cue-monitor'],
            'service_api_url': 'http://localhost:8795/v1',
            'search_pattern': '.*v1.*'
        }

        super(Cue, self).__init__(service_params)
