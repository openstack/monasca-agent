# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP

import logging
import os
import yaml

from monasca_setup import agent_config
from monasca_setup.detection import Plugin

log = logging.getLogger(__name__)


class System(Plugin):

    """No configuration here, the system metrics are assumed so this is either on or off.

    """
    system_metrics = ['network', 'disk', 'load', 'memory', 'cpu']

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        self.available = True

    def build_config(self):
        """Build the configs for the system metrics as Plugin objects and return.

        """
        config = agent_config.Plugins()
        for metric in System.system_metrics:
            try:
                with open(os.path.join(self.template_dir, 'conf.d/' + metric + '.yaml'), 'r') as metric_template:
                    default_config = yaml.safe_load(metric_template.read())
                config[metric] = default_config
                if self.args:
                    for arg in self.args:
                        config[metric]['instances'][0][arg] = self.literal_eval(self.args[arg])
                log.info('\tConfigured {0}'.format(metric))
            except (OSError, IOError):
                log.info('\tUnable to configure {0}'.format(metric))
                continue

        return config

    def dependencies_installed(self):
        return True
