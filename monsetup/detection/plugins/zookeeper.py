import logging
import os

import yaml

import monsetup.agent_config
import monsetup.detection

log = logging.getLogger(__name__)


class Zookeeper(monsetup.detection.Plugin):

    """Detect Zookeeper daemons and setup configuration to monitor them.

    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        if monsetup.detection.find_process_cmdline('zookeeper') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = monsetup.agent_config.Plugins()
        # First watch the process
        log.info("\tWatching the zookeeper process.")
        config.merge(monsetup.detection.watch_process(['zookeeper']))

        log.info("\tEnabling the zookeeper plugin")
        with open(os.path.join(self.template_dir, 'conf.d/zk.yaml.example'), 'r') as zk_template:
            zk_config = yaml.load(zk_template.read())
        config['zk'] = zk_config

        return config

    def dependencies_installed(self):
        # The current plugin just does a simple socket connection to zookeeper and
        # parses the stat command
        return True
