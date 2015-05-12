import logging

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)


class HostAlive(monasca_setup.detection.Plugin):
    """ Setup an host_alive check according to the passed in args.
        Despite being a detection plugin this plugin does no detection and will be a noop without arguments.
        Expects two space seperated arguments hostname and type. Type can be either 'ssh' or 'ping'. For example:
        'monasca-setup -d hostalive -a "hostname=remotebox type=ping"'
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """
        if self.args is not None and 'hostname' in self.args and 'type' in self.args:
            self.available = True
        else:
            self.available = False

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        log.info("\tEnabling {type} host check for {hostname}".format(**self.args))
        config['host_alive'] = {'init_config': None, 'instances': [{'name': "{hostname} {type}".format(**self.args),
                                                                    'host_name': self.args['hostname'],
                                                                    'alive_test': self.args['type']}]}

        return config

    def dependencies_installed(self):
        return True
