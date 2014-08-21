import os

import yaml

import monsetup.agent_config
import monsetup.detection


class Postfix(monsetup.detection.Plugin):

    """If postfix is running install the default config.

    """
    # todo this is is disabled as postfix requires passwordless sudo for the
    # monasca-agent user, a bad practice

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        if monsetup.detection.find_process_name('postfix') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        # A bit silly to parse the yaml only for it to be converted back but this
        # plugin is the exception not the rule
        with open(os.path.join(self.template_dir, 'conf.d/postfix.yaml.example'), 'r') as postfix_template:
            default_net_config = yaml.load(postfix_template.read())
        config = monsetup.agent_config.Plugins()
        config['postfix'] = default_net_config
        return config

    def dependencies_installed(self):
        return True
