import logging

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)


class SwiftDispersion(monasca_setup.detection.Plugin):

    """Detect Swift proxy daemon and setup configuration for swift-dispersion.

    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """
        if monasca_setup.detection.find_process_cmdline('swift-proxy-server') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        log.info("\tEnabling the swift-dispersion plugin")
        config['swift_dispersion'] = {'init_config': None, 'instances': [{'name': 'swift-dispersion'}]}

        return config
