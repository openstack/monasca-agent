import logging

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)


class HostAlive(monasca_setup.detection.ArgsPlugin):
    """ Setup an host_alive check according to the passed in args.
        Despite being a detection plugin this plugin does no detection and will be a noop without arguments.
        Expects two space seperated arguments hostname and type. Type can be either 'ssh' or 'ping'. hostname
        can be a comma seperated list of hosts.
        Examples:
        'monasca-setup -d hostalive -a "hostname=remotebox type=ping"'
        'monasca-setup -d hostalive -a "hostname=remotebox,remotebox2 type=ssh"'
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """
        self.available = self._check_required_args(['hostname', 'type'])
        # Ideally the arg would be called hostnames but leaving it hostname to avoid breaking backward compatibility

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        log.info("\tEnabling {type} host check for {hostname}".format(**self.args))
        instances = []
        for hostname in self.args['hostname'].split(','):
            # Since the naming in the args and in the config don't match build_instance is only good for dimensions
            instance = self._build_instance([])
            instance.update({'name': "{0} {1}".format(hostname, self.args['type']),
                             'host_name': hostname,
                             'alive_test': self.args['type']})
            instances.append(instance)

        config['host_alive'] = {'init_config': None, 'instances': instances}

        return config

