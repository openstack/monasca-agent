# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging
import os

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)

# Defaults
supervisord_conf = '/root/.supervisord.cnf'
supervisord_server_name = 'server0'


class Supervisord(monasca_setup.detection.Plugin):
    """Detect supervisord process and setup configuration for monitoring.

        This plugin needs connection info for supervisord setup. There are two
        ways to provide it, either by a file placed in /root/.supervisord.cnf
        or by specifying the following arguments:
            - server (req, arbitrary name to identify the supervisord server)
            - socket (opt, required for socket connection type)
            - host (opt, defaults to localhost)
            - port (opt, defaults to 9001)
            - user (opt, only if username is configured)
            - password (opt, only if password is configured)
            - process_regex (opt, regex patterns for processes to monitor)
            - process_names (opt, process to monitor by name)
        process_regex and process_names are comma separated lists

        The file at /root/.supervisord.cnf should have this format:
        [client]
            server=server0
            socket=unix:///var/run//supervisor.sock
            process_names=apache2,webapp,java
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """
        found_process = (monasca_setup.detection.
                         find_process_cmdline('supervisord'))
        has_args_or_conf_file = (self.args is not None or
                                 os.path.isfile(supervisord_conf))
        self.available = found_process is not None and has_args_or_conf_file
        if not self.available:
            if not found_process:
                log.info('Supervisord process does not exist.')
            elif not has_args_or_conf_file:
                log.warning(('Supervisord process exists but '
                             'configuration file was not found and '
                             'no arguments were given.'))

    def _get_config(self):
        """Set the configuration to be used for connecting to supervisord
        :return:
        """
        # Set defaults and read config or use arguments
        if self.args is None:
            self.server = supervisord_server_name
            self.socket = None
            self.host = None
            self.port = None
            self.user = None
            self.password = None
            self.process_regex = None
            self.process_names = None
            self.process_details_check = None
            self.process_uptime_check = None

            self._read_config(supervisord_conf)
        else:
            self.server = self.args.get('server', supervisord_server_name)
            self.socket = self.args.get('socket')
            self.host = self.args.get('host')
            self.port = self.args.get('port')
            self.user = self.args.get('user')
            self.password = self.args.get('pass')
            self.process_regex = self.args.get('proc_regex')
            self.process_names = self.args.get('proc_names')
            self.process_details_check = self.args.get('proc_details_check')
            self.process_uptime_check = self.args.get('proc_uptime_check')

    def _read_config(self, config_file):
        """Read the configuration setting member variables as appropriate.
        :param config_file: The filename of the configuration to read and parse
        """
        # Read the supervisord config file to extract the needed variables.
        client_section = False
        try:
            with open(config_file, "r") as conf:
                for row in conf:
                    if "[client]" in row:
                        client_section = True
                        log.info("\tUsing client credentials from {:s}".format(config_file))
                        pass
                    if client_section:
                        if "server=" in row:
                            self.server = row.split("=")[1].strip()
                        if "socket=" in row:
                            self.socket = row.split("=")[1].strip()
                        if "host=" in row:
                            self.host = row.split("=")[1].strip()
                        if "port=" in row:
                            self.port = row.split("=")[1].strip()
                        if "user=" in row:
                            self.user = row.split("=")[1].strip()
                        if "pass=" in row:
                            self.password = row.split("=")[1].strip()
                        if "proc_regex=" in row:
                            self.process_regex = row.split("=")[1].strip()
                        if "proc_names=" in row:
                            self.process_names = row.split("=")[1].strip()
                        if "proc_details_check=" in row:
                            self.process_details_check = row.split("=")[1].strip()
                        if "proc_uptime_check=" in row:
                            self.process_uptime_check = row.split("=")[1].strip()
        except IOError:
            log.error("\tI/O error reading {:s}".format(config_file))

    @staticmethod
    def _split_list(to_split):
        return [x.strip() for x in to_split.split(',')]

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        # First watch the process
        config.merge(monasca_setup.detection.watch_process(['supervisord'],
                                                           'supervisord',
                                                           exact_match=False))
        log.info("\tWatching the supervisord process.")

        try:
            self._get_config()
            instance_config = {'name': self.server}
            if self.socket is not None:
                instance_config['socket'] = self.socket
            if self.host is not None:
                instance_config['host'] = self.host
            if self.port is not None:
                instance_config['port'] = self.port
            if self.user is not None:
                instance_config['user'] = self.user
            if self.password is not None:
                instance_config['pass'] = self.password
            if self.process_regex is not None:
                instance_config['proc_regex'] = self._split_list(self.process_regex)
            if self.process_names is not None:
                instance_config['proc_names'] = self._split_list(self.process_names)
            if self.process_details_check is not None:
                instance_config['proc_details_check'] = self.process_details_check
            if self.process_uptime_check is not None:
                instance_config['proc_uptime_check'] = self.process_uptime_check

            config['supervisord'] = {'init_config': None, 'instances': [instance_config]}
        except Exception:
            log.exception('Error configuring the supervisord check plugin')

        return config

    def dependencies_installed(self):
        return True
