# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import logging
import os

import yaml

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)


class Zookeeper(monasca_setup.detection.Plugin):

    """Detect Zookeeper daemons and setup configuration to monitor them.

    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        if monasca_setup.detection.find_process_cmdline('org.apache.zookeeper') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = monasca_setup.agent_config.Plugins()
        # First watch the process
        log.info("\tWatching the zookeeper process.")
        config.merge(monasca_setup.detection.watch_process(['org.apache.zookeeper.server'], 'zookeeper',
                                                           exact_match=False))

        log.info("\tEnabling the zookeeper plugin")
        with open(os.path.join(self.template_dir, 'conf.d/zk.yaml.example'), 'r') as zk_template:
            zk_config = yaml.load(zk_template.read())
        config['zk'] = zk_config

        return config

    def dependencies_installed(self):
        # The current plugin just does a simple socket connection to zookeeper and
        # parses the stat command
        return True
