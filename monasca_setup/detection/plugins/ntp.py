import logging
import os
import re

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
        if os.path.exists('/etc/ntp.conf'):
            server = re.compile('server (.*)')
            with open('/etc/ntp.conf', 'r') as ntp_config:
                match = server.search(ntp_config.read())
            if match is None:
                ntp_server = 'pool.ntp.org'
            else:
                ntp_server = match.group(1)
        else:
            ntp_server = 'pool.ntp.org'
        config['ntp'] = {'init_config': None, 'instances': [{'name': ntp_server, 'host': ntp_server}]}

        return config

    def dependencies_installed(self):
        try:
            import ntplib
        except ImportError:
            return False
        else:
            return True
