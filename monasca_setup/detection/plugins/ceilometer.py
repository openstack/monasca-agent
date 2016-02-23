# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import monasca_setup.detection


class Ceilometer(monasca_setup.detection.ServicePlugin):

    """Detect Ceilometer daemons and setup configuration to monitor them."""

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'telemetry',
            'process_names': ['ceilometer-agent-compute', 'ceilometer-agent-central',
                              'ceilometer-agent-notification', 'ceilometer-collector',
                              'ceilometer-alarm-notifier', 'ceilometer-alarm-evaluator',
                              'ceilometer-api'],
            # TO DO: Update once the health check is implemented in Ceilometer
            # 'service_api_url': 'http://localhost:8777/v2/health',
            # 'search_pattern' : '.*200 OK.*',
            'service_api_url': '',
            'search_pattern': ''
        }

        super(Ceilometer, self).__init__(service_params)
