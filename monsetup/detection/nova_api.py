from . import Plugin, find_process_cmdline, watch_process
from monsetup import agent_config


class NovaAPI(Plugin):
    """Detect the Nova-API daemon and setup configuration to monitor it."""

    def _detect(self):
        """Run detection"""
        if find_process_cmdline('nova-api') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = agent_config.Plugins()
        # First watch the Nova-API process
        log.info("\tWatching the nova API process.")
        config.merge(watch_process(['nova-api']))

        # Next setup an active http_status check on the API
        config['http_check'] = {'init_config': None,
                                 'instances': [{'name': 'nova_api',
                                                'collect_response_time': true,
                                                'match_pattern': '.*servers.*',
                                                'timeout': '10',
                                                'url': 'http://localhost/v2',
                                                'use_keystone': 'true'}]}

        return config

    def dependencies_installed(self):
        return True

