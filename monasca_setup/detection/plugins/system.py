import logging
import os
import yaml

from monasca_setup.detection import Plugin
from monasca_setup import agent_config

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
                    default_config = yaml.load(metric_template.read())
                config[metric] = default_config
                log.info('\tConfigured {0}'.format(metric))
            except (OSError, IOError):
                log.info('\tUnable to configure {0}'.format(metric))
                continue

        return config

    def dependencies_installed(self):
        return True
