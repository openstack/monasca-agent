# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import logging
import os

from monasca_setup import agent_config
from monasca_setup.detection import Plugin

log = logging.getLogger(__name__)


class Crash(Plugin):
    """Detect if kdump is installed and enabled and setup configuration to
       monitor for crash dumps.
    """

    def _detect(self):
        """Run detection, set self.available True if a crash kernel is loaded.
        """
        loaded = '/sys/kernel/kexec_crash_loaded'
        if os.path.isfile(loaded):
            with open(loaded, 'r') as fh:
                if fh.read().strip() == '1':
                    self.available = True

    def build_config(self):
        """Build the config as a Plugin object and return it.
        """
        log.info('\tEnabling the Monasca crash dump healthcheck')
        config = agent_config.Plugins()

        config['crash'] = {
            'init_config': None,
            'instances': [{'name': 'crash_stats'}]
        }

        return config

    def dependencies_installed(self):
        return True
