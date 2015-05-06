import logging
import os
import yaml

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)


class Postfix(monasca_setup.detection.Plugin):
    """If postfix is running install the default config.
    """
    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        if monasca_setup.detection.find_process_cmdline('postfix') is not None:
            # Test for sudo access
            # TODO: don't hardcode the user. Need to get it from the arguments to monasca_setup
            test_sudo = os.system('sudo -l -U mon-agent find /var/spool/postfix/incoming -type f > /dev/null')
            if test_sudo != 0:
                log.info("Postfix found but the required sudo access is not configured.\n\t" +
                         "Refer to plugin documentation for more detail")
                return False

        self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        # A bit silly to parse the yaml only for it to be converted back but this
        # plugin is the exception not the rule
        with open(os.path.join(self.template_dir, 'conf.d/postfix.yaml.example'), 'r') as postfix_template:
            default_net_config = yaml.load(postfix_template.read())
        config = monasca_setup.agent_config.Plugins()
        config['postfix'] = default_net_config
        return config

    def dependencies_installed(self):
        return True
