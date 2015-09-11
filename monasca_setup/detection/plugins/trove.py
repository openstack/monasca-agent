import logging
import monasca_setup.detection

log = logging.getLogger(__name__)


class Trove(monasca_setup.detection.ServicePlugin):

    """Detect Trove daemons and setup configuration to monitor them."""

    def __init__(self, template_dir, overwrite=True, args=None):

        service_api_url = "http://localhost:8779"
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
            'service_name': 'database',
            'process_names': ['trove-api', 'trove-taskmanager', 'trove-conductor'],
            'service_api_url': service_api_url,
            'search_pattern': '.*v1.*'
        }

        super(Trove, self).__init__(service_params)
