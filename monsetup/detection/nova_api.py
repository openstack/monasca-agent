import logging
from . import Plugin, find_process_cmdline, watch_process, service_api_check
from monsetup import agent_config

log = logging.getLogger(__name__)

class NovaAPI(Plugin):
    """Detect the Nova-API daemon and setup configuration to monitor it."""

    def _detect(self):
        """Run detection"""
        if find_process_cmdline('nova-api') is not None:
            log.info('Found nova-api')
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = agent_config.Plugins()
        # First watch the Nova-API process
        log.info("\tWatching the nova API process.")
        config.merge(watch_process(['nova-api']))

        # Next setup an active http_status check on the API
        log.info("\tConfiguring an http_check for the nova API.")
        config.merge(service_api_check('nova_api', 'http://localhost:5000/v2.0', '.*identity-v2.*'))

        return config

    def dependencies_installed(self):
        return True

