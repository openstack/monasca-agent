import os

import yaml

from monsetup.detection import Plugin
from monsetup import agent_config


class Network(Plugin):

    """No configuration here, working networking is assumed so this is either on or off.

    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        # A bit silly to parse the yaml only for it to be converted back but this
        # plugin is the exception not the rule
        with open(os.path.join(self.template_dir, 'conf.d/network.yaml'), 'r') as network_template:
            default_net_config = yaml.load(network_template.read())
        config = agent_config.Plugins()
        config['network'] = default_net_config
        return config

    def dependencies_installed(self):
        return True
