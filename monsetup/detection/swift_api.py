import logging
from . import Plugin, find_process_cmdline, watch_process, service_api_check
from monsetup import agent_config

log = logging.getLogger(__name__)


class SwiftAPI(Plugin):

    """Detect the Swift-API daemon and setup configuration to monitor it."""

    def _detect(self):
        """Run detection"""
        self.service_name = 'swift'
        self.process_name = 'swift-proxy-server'
        if find_process_cmdline(self.process_name) is not None:
            log.info('Found {0}'.format(self.process_name))
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = agent_config.Plugins()
        # First watch the Swift-API process
        log.info("\tMonitoring the swift API process.")
        config.merge(watch_process([self.process_name], self.service_name))

        # Next setup an active http_status check on the API
        log.info("\tConfiguring an http_check for the swift API.")
        config.merge(
            service_api_check(self.process_name, 'http://localhost:8080/healthcheck', '.*OK.*', self.service_name))

        return config

    def dependencies_installed(self):
        return True
