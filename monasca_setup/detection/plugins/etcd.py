import logging

import monasca_setup.agent_config
import monasca_setup.detection
from monasca_setup.detection.utils import find_process_name

log = logging.getLogger(__name__)


class Etcd(monasca_setup.detection.Plugin):

    """Detect Etcd daemons and setup configuration to monitor them.
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """
        if find_process_name('etcd') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        # First watch the process
        config.merge(monasca_setup.detection.watch_process(['etcd'], component='etcd'))
        log.info("\tWatching the etcd process.")

        log.info("\tEnabling the etcd plugin")
        config['etcd'] = {'init_config': None, 'instances': [{'url': 'http://localhost:2379'}]}

        return config
