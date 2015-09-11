import logging
import monasca_setup.detection

log = logging.getLogger(__name__)


class Ironic(monasca_setup.detection.ServicePlugin):

    """Detect Ironic daemons and setup configuration to monitor them."""

    def __init__(self, template_dir, overwrite=True, args=None):
        service_api_url = "http://localhost:6385"
        if isinstance(args, str):
            try:
                # Turn 'service_api_url=url' into
                # dict {'service_api_url':'url'}
                args_dict = dict([item.split('=') for item
                                  in args.split()])

                if "service_api_url" in args_dict:
                    service_api_url = args_dict['service_api_url']
            except Exception:
                log.exception('Error parsing detection arguments')

        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'Baremetal',
            'process_names': ['ironic-api', 'ironic-conductor'],
            'service_api_url': service_api_url,
            'search_pattern': '.*200 OK.*',
        }

        super(Ironic, self).__init__(service_params)
