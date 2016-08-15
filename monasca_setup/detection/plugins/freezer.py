# (C) Copyright 2016 Hewlett Packard Enterprise Development LP

import monasca_setup.detection


class FreezerAPI(monasca_setup.detection.ServicePlugin):
    """Detect a running Freezer API server."""

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'backup',
            'process_names': ['freezer-api'],
            'service_api_url': 'http://127.0.0.1:9090/healthcheck',
            'search_pattern': '.*OK.*'
        }

        super(FreezerAPI, self).__init__(service_params)


class FreezerScheduler(monasca_setup.detection.ServicePlugin):
    """Detect a running Freezer client-side scheduler."""

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'backup',
            'process_names': ['freezer-scheduler'],
            'service_api_url': None,
            'search_pattern': None
        }

        super(FreezerScheduler, self).__init__(service_params)
