import logging
from . import Plugin, find_process_cmdline, watch_process
from monsetup import agent_config

log = logging.getLogger(__name__)


class Swift(Plugin):

    """Detect Swift daemons and setup configuration to monitor them."""

    def _detect(self):
        """Run detection"""
        self.swift_processes = ['swift-container-updater', 'swift-account-auditor',
                                'swift-object-replicator', 'swift-container-replicator',
                                'swift-object-auditor', 'swift-container-auditor',
                                'swift-account-reaper', 'swift-container-sync',
                                'swift-account-replicator', 'swift-object-updater',
                                'swift-object-server', 'swift-account-server',
                                'swift-container-server']
        self.found_processes = []

        for process in self.swift_processes:
            if find_process_cmdline(process) is not None:
                log.info('Found {0} swift process'.format(process))
                self.found_processes.append(process)
        if len(self.found_processes) > 0:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = agent_config.Plugins()
        for process in self.found_processes:
            # Watch the Swift processes
            log.info("\tMonitoring the {0} swift process.".format(process))
            config.merge(watch_process([process], 'swift'))

        return config

    def dependencies_installed(self):
        return True
