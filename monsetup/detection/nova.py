from . import Plugin, find_process_cmdline, watch_process
from monsetup import agent_config


class Nova(Plugin):
    """Detect Nova daemons and setup configuration to monitor them."""

    def _detect(self):
        """Run detection"""
        if find_process_cmdline('nova-compute') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = agent_config.Plugins()
        # First watch the Nova processes
        log.info("\tWatching the nova processes.")
        config.merge(watch_process(['nova-compute', 'nova-conductor',
                                    'nova-cert', 'nova-network',
                                    'nova-scheduler', 'nova-novncproxy',
                                    'nova-xvpncproxy', 'nova-consoleauth',
                                    'nova-objectstore']))

        return config

    def dependencies_installed(self):
        return True

