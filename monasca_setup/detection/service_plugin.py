import logging
import psutil
from urlparse import urlparse

from plugin import Plugin

from monasca_setup import agent_config
from monasca_setup.detection import find_process_cmdline
from monasca_setup.detection import service_api_check
from monasca_setup.detection import watch_process


log = logging.getLogger(__name__)


class ServicePlugin(Plugin):
    """Base class implemented by the monasca-agent plugin detection classes for OpenStack Services.
        Detection plugins inheriting from this class can easily setup up processes to be watched and
        a http endpoint to be checked.

        The http check can be skipped by specifying the argument 'disable_http_check'
    """

    def __init__(self, kwargs):
        self.args = kwargs.get('args')
        self.service_name = kwargs['service_name']
        self.process_names = kwargs['process_names']
        self.service_api_url = kwargs.get('service_api_url')
        self.search_pattern = kwargs['search_pattern']

        super(ServicePlugin, self).__init__(kwargs['template_dir'], kwargs['overwrite'])

    def _detect(self):
        """Run detection.

        """
        self.found_processes = []

        for process in self.process_names:
            if find_process_cmdline(process) is not None:
                self.found_processes.append(process)
        if len(self.found_processes) > 0:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = agent_config.Plugins()
        for process in self.found_processes:
            # Watch the service processes
            log.info("\tMonitoring the {0} {1} process.".format(process, self.service_name))
            config.merge(watch_process([process], self.service_name, process, exact_match=False))

        # Skip the http_check if disable_http_check is set
        if self.args is not None:
            args_dict = dict([a.split('=') for a in self.args.split()])
            if args_dict.get('disable_http_check', default=False):
                self.service_api_url = None
                self.search_pattern = None

        if self.service_api_url and self.search_pattern:
            # Check if there is something listening on the host/port
            parsed = urlparse(self.service_api_url)
            host, port = parsed.netloc.split(':')
            listening = []
            for connection in psutil.net_connections():
               if connection.status == psutil.CONN_LISTEN and connection.laddr[1] == int(port):
                   listening.append(connection.laddr[0])

            if len(listening) > 0:
                # If not listening on localhost or ips then use another local ip
                if host == 'localhost' and len(set(['0.0.0.0', '::', '::1']) & set(listening)) == 0:
                    api_url = listening[0] + ':' + port
                else:
                    api_url = self.service_api_url

                # Setup an active http_status check on the API
                log.info("\tConfiguring an http_check for the {0} API.".format(self.service_name))
                config.merge(service_api_check(self.service_name + '-api', api_url,
                                           self.search_pattern, self.service_name))
            else:
                log.info("\tNo process found listening on {0} ".format(port) +
                         "skipping setup of http_check for the {0} API." .format(self.service_name))

        return config

    def dependencies_installed(self):
        """Return True if dependencies are installed.

        """
        return True
