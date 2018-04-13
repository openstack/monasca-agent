# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

"""Detection Plugin for MK_Livestatus Nagios/Icinga Event Broker Module
   This monasca_setup detection plugin will determine if either Nagios or
   Icinga is configured on this system, if that configuration includes the
   MK_Livestatus module, if that module's configured socket path exists
   (which should be the case as long as Nagios/Icinga is running), and if
   the Monasca Agent's user can read it.  If all these criteria are met, the
   mk_livestatus Agent plugin will be enabled with a basic configuration that
   polls all services and all hosts.
"""
import logging
import monasca_setup.agent_config
import monasca_setup.detection
import os

log = logging.getLogger(__name__)

# List several common locations of Nagios/Icinga configuration files to scan
nagios_cfg_files = ['/etc/nagios/nagios.cfg',
                    '/etc/nagios/nagios.cfg',
                    '/etc/nagios3/nagios.cfg',
                    '/etc/nagios4/nagios.cfg',
                    '/usr/local/nagios/nagios.cfg',
                    '/usr/local/nagios/etc/nagios.cfg',
                    '/etc/icinga/icinga.cfg',
                    '/usr/local/icinga/icinga.cfg',
                    '/usr/local/icinga/etc/icinga.cfg']
agent_user = 'monasca-agent'


class MKLivestatus(monasca_setup.detection.Plugin):
    """Detect MK_Livestatus Nagios Event Broker and verify permissions
    """

    def _find_socket_path(self):
        """Search common Nagios/Icinga config file locations for mk_livestatus
           broker module socket path
        """
        # Search likely Nagios/Icinga config file locations
        for cfg_file in nagios_cfg_files:
            if os.path.isfile(cfg_file):
                # Search the file for the mk_livestatus socket
                with open(cfg_file) as cfg:
                    for line in cfg:
                        if line.startswith('broker_module') and line.find('mk') > 0:
                            return line.split(' ')[-1].rstrip()

    def _detect(self):
        """Set self.available=True if module is installed and path is readable
        """
        socket_path = self._find_socket_path()
        if self.dependencies_installed and socket_path is not None:
            if os.path.exists(socket_path):
                # Is it readable by the monasca-agent user?
                test_readable = os.system(
                    'sudo -u {0} ls -1 {1} >/dev/null 2>&1'.format(agent_user, socket_path))
                if test_readable != 0:
                    log.info("Not configuring MK_Livestatus:")
                    log.info("\t{0} exists but is not readable by {1}.".format(socket_path,
                                                                               agent_user))
                else:
                    self.available = True
                    self.socket_path = socket_path

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        log.info("\tEnabling the mk_livestatus plugin")

        config['mk_livestatus'] = {'init_config': {'socket_path': self.socket_path},
                                   'instances': [{'check_type': 'service'},
                                                 {'name': 'nagios.host_status',
                                                  'check_type': 'host'}]}

        log.info("\tConfigured for all services and hosts")
        return config

    def dependencies_installed(self):
        try:
            import socket  # noqa
        except ImportError:
            return False
        else:
            return True
