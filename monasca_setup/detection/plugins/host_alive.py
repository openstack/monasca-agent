# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development LP
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)


class HostAlive(monasca_setup.detection.ArgsPlugin):
    """Setup an host_alive check according to the passed in args.
       Despite being a detection plugin, this plugin does no detection and
       will be a NOOP without arguments.  Expects two space-separated
       arguments, 'hostname' and 'type,' where the former is a comma-separated
       list of hosts, and the latter can be either 'ssh' or 'ping'.
       Examples:

       monasca-setup -d hostalive -a "hostname=remotebox type=ping"

       monasca-setup -d hostalive -a "hostname=rb,rb2 target_hostname=,rb2-nic2 type=ssh"
    """

    DEFAULT_PING_TIMEOUT = 1
    DEFAULT_SSH_TIMEOUT = 2
    DEFAULT_SSH_PORT = 22

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """
        self.available = self._check_required_args(['hostname', 'type'])
        # Ideally, the arg would be called 'hostnames,' but leaving it
        # 'hostname' avoids breaking backward compatibility.

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        log.info("\tEnabling {type} host check for {hostname}".format(**self.args))
        instances = []
        for hostname in self.args['hostname'].split(','):
            # Since the naming in the args and in the config don't match,
            #  build_instance is only good for dimensions
            instance = self._build_instance([])
            instance.update({'name': "{0} {1}".format(hostname,
                                                      self.args['type']),
                             'host_name': hostname,
                             'alive_test': self.args['type']})
            instances.append(instance)
        if 'target_hostname' in self.args:
            index = 0
            network_names_to_check = self.args['target_hostname'].split(',')
            for target_hostname in network_names_to_check:
                if target_hostname:
                    if index >= len(instances):
                        raise Exception('Too many target_hostname values')
                    instance = instances[index]
                    instance.update({'target_hostname': target_hostname})
                index += 1

        config['host_alive'] = {
            'init_config': {'ping_timeout': self.DEFAULT_PING_TIMEOUT,
                            'ssh_timeout': self.DEFAULT_SSH_TIMEOUT,
                            'ssh_port': self.DEFAULT_SSH_PORT},
            'instances': instances}

        return config
