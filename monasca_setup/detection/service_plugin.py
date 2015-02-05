import logging

from plugin import Plugin

from monasca_setup import agent_config
from monasca_setup.detection import find_process_cmdline
from monasca_setup.detection import service_api_check
from monasca_setup.detection import watch_process


log = logging.getLogger(__name__)


class ServicePlugin(Plugin):

    """Base class implemented by the monasca-agent plugin detection classes

       for OpenStack Services
    """

    def __init__(self, kwargs):
        self.service_name = kwargs['service_name']
        self.process_names = kwargs['process_names']
        self.service_api_url = kwargs['service_api_url']
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

        if self.service_api_url and self.search_pattern:
            # Setup an active http_status check on the API
            log.info("\tConfiguring an http_check for the {0} API.".format(self.service_name))
            config.merge(service_api_check(self.service_name + '-api', self.service_api_url,
                                           self.search_pattern, self.service_name))

        return config

    def dependencies_installed(self):
        """Return True if dependencies are installed.

        """
        return True
