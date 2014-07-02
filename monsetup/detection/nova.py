import logging
from . import Plugin, find_process_cmdline, watch_process
from monsetup import agent_config

log = logging.getLogger(__name__)


class Nova(Plugin):
    """Detect Nova daemons and setup configuration to monitor them."""

    def _detect(self):
        """Run detection"""
        self.nova_processes = ['nova-compute', 'nova-conductor',
                               'nova-cert', 'nova-network',
                               'nova-scheduler', 'nova-novncproxy',
                               'nova-xvpncproxy', 'nova-consoleauth',
                               'nova-objectstore']
        self.found_processes = []

        for process in self.nova_processes:
            if find_process_cmdline(process) is not None:
                log.info('Found {0} nova process'.format(process))
                self.found_processes.append(process)
        if len(self.found_processes) > 0:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = agent_config.Plugins()
        for process in self.found_processes:
            # Watch the Nova processes
            log.info("\tMonitoring the {0} nova process.".format(process))
            config.merge(watch_process([process], 'nova'))

        return config

    def dependencies_installed(self):
        return True

