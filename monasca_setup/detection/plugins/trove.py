import logging
import monasca_setup.detection

log = logging.getLogger(__name__)


class Trove(monasca_setup.detection.ServicePlugin):

    """Detect Trove daemons and setup configuration to monitor them."""

    def __init__(self, template_dir, overwrite=True, args=None):

        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'database',
            'process_names': ['trove-api', 'trove-taskmanager', 'trove-conductor'],
            'service_api_url': "http://localhost:8779",
            'search_pattern': '.*v1.*'
        }

        super(Trove, self).__init__(service_params)
