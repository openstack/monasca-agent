# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
# Copyright 2017 FUJITSU LIMITED
#
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
import os

import yaml

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)

_ZOOKEEPER_DEFAULT_CONFIG_PATH = '/etc/zookeeper/conf/zoo.cfg'
_ZOOKEEPER_DEFAULT_IP = 'localhost'
_ZOOKEEPER_DEFAULT_PORT = 2181


class Zookeeper(monasca_setup.detection.Plugin):

    """Detect Zookeeper daemons and setup configuration to monitor them.

    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        process_found = monasca_setup.detection.find_process_cmdline('org.apache.zookeeper')
        self._cfg_file = self._get_config_file(process_found) if process_found else None
        has_config_file = self._cfg_file and os.path.isfile(self._cfg_file)

        self.available = process_found and has_config_file

        if not self.available:
            err_str = 'Plugin for Zookeeper will not be configured.'
            if not process_found:
                log.error('Zookeeper process has not been found: {0}'.format(err_str))
            elif not has_config_file:
                log.error('Zookeeper plugin cannot find configuration file: {0}. {1}'.format(self._cfg_file, err_str))

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = monasca_setup.agent_config.Plugins()
        host, port = self._read_config_file(self._cfg_file)
        # First watch the process
        log.info("\tWatching the zookeeper process.")
        config.merge(monasca_setup.detection.watch_process(['org.apache.zookeeper.server'], 'zookeeper',
                                                           exact_match=False))

        log.info("\tEnabling the zookeeper plugin")
        config['zk'] = {
            'init_config': None, 'instances':
            [{'name': host, 'host': host, 'port': port, 'timeout': 3}]
        }

        return config

    def dependencies_installed(self):
        # The current plugin just does a simple socket connection to zookeeper and
        # parses the stat command
        return True  # pragma: no cover

    @staticmethod
    def _get_config_file(process):
        # Config file should be on the last place in cmdline
        cfg = process.as_dict(['cmdline'])['cmdline'][-1]
        # check if the last value in cmdline is a file
        # if not return default config file
        if os.path.isfile(cfg):
            log.debug('Found zookeeper config file: {0}'.format(cfg))
            return cfg
        log.debug('Missing zookeeper config file. Using default file: {0}'.
                  format(_ZOOKEEPER_DEFAULT_CONFIG_PATH))
        return _ZOOKEEPER_DEFAULT_CONFIG_PATH

    @staticmethod
    def _read_config_file(cfg_file):
        ip_address = _ZOOKEEPER_DEFAULT_IP
        port = _ZOOKEEPER_DEFAULT_PORT
        try:
            cfg = open(cfg_file, 'r')
            for line in cfg:
                if 'clientPortAddress' in line:
                    log.debug('Found clientPort in config file: {0}'.format(line))
                    ip_address = line.split('=')[1].strip()
                if 'clientPort' in line and 'clientPortAddress' not in line:
                    log.debug('Found clientPortAddress in config file: {0}'.format(line))
                    port = int(line.split('=')[1].strip())
        except Exception as ex:
            log.error('Failed to parse %s', cfg_file)
            log.exception(ex)
            return None
        return ip_address, port
