import logging
import os

import yaml

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)


class Ntp(monasca_setup.detection.Plugin):
    """Detect NTP daemon and setup configuration to monitor them.
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """
        if monasca_setup.detection.find_process_cmdline('ntp') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        log.info("\tEnabling the ntp plugin")
        with open(os.path.join(self.template_dir, 'conf.d/ntp.yaml.example'), 'r') as ntp_template:
            ntp_config = yaml.load(ntp_template.read())
        config['ntp'] = ntp_config

        return config

    def dependencies_installed(self):
        try:
            import ntplib
        except ImportError:
            return False
        else:
            return True
