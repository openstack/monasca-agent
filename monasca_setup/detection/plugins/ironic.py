import logging
import monasca_setup.detection

log = logging.getLogger(__name__)


class Ironic(monasca_setup.detection.ServicePlugin):

    """Detect Ironic daemons and setup configuration to monitor them."""

    def __init__(self, template_dir, overwrite=True, args=None):

        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'baremetal',
            'process_names': ['ironic-api', 'ironic-conductor'],
            'service_api_url': "http://localhost:6385",
            'search_pattern': '.*v1.*',
        }

        super(Ironic, self).__init__(service_params)
