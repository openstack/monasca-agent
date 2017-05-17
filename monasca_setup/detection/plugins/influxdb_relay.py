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

from oslo_utils import importutils

from monasca_setup import agent_config
from monasca_setup import detection
from monasca_setup.detection import utils

LOG = logging.getLogger(__name__)


class InfluxDBRelay(detection.Plugin):
    """Detects influxdb-relay and sets up its monitoring

    Monitored items:

    * process
    * http_check

    """

    PROC_NAME = 'influxdb-relay'
    """Name of the InfluxDB Relay process expected to be found in the system"""
    DEFAULTS = {
        'bind_address': '127.0.0.1',
        'bind_port': 9096
    }
    RELAY_NODE_ARG_NAME = 'influxdb_relay_node'

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """

        proc = utils.find_process_name(self.PROC_NAME)
        process_found = proc is not None

        config_file = self._get_config_file(proc) if process_found else None
        config_file_found = config_file is not None

        dependencies_installed = self.dependencies_installed()

        self.available = (process_found and config_file_found
                          and dependencies_installed)

        if not self.available:
            err_chunks = []
            if not process_found:
                err_chunks.append('\tinfluxdb-relay plugin cannot locate '
                                  '"%s" process.' % self.PROC_NAME)
            elif not config_file_found:
                err_chunks.append('\tinfluxdb-relay plugin cannot locate '
                                  'configuration file.')
            elif not dependencies_installed:
                err_chunks.append('\tinfluxdb-relay plugin requires "toml" '
                                  'to be installed')
            LOG.error('Plugin for influxdb-relay will not be configured.\n'
                      'Following issue have to be resolved: %s' %
                      '\n'.join(err_chunks))
        else:
            self._config = self._load_config(config_file)

    def build_config(self):
        """Build the config as a Plugins object and return."""
        LOG.info("\tEnabling the influxdb-relay check")
        config = agent_config.Plugins()

        config.merge(self._monitor_process())
        config.merge(self._monitor_endpoint())

        return config

    def _monitor_process(self):
        LOG.info("\tMonitoring the influxdb-relay process")

        dimensions = {}
        if self.args and self.args.get(self.RELAY_NODE_ARG_NAME):
            dimensions.update({self.RELAY_NODE_ARG_NAME: self.args.get(self.RELAY_NODE_ARG_NAME)})

        return detection.watch_process([self.PROC_NAME],
                                       service='influxdb',
                                       component='influxdb-relay',
                                       exact_match=False,
                                       dimensions=dimensions)

    def _monitor_endpoint(self):
        config = agent_config.Plugins()
        http_conf = self._config.get('http', None)
        if isinstance(http_conf, list):
            http_conf = http_conf[0]

        if http_conf:
            host, port = self._explode_bind_address(http_conf)
            listening = utils.find_addrs_listening_on_port(port)
            if listening:
                LOG.info("\tMonitoring the influxdb-relay ping endpoint")

                dimensions = {'service': 'influxdb',
                              'component': 'influxdb-relay'}
                if self.args and self.args.get(self.RELAY_NODE_ARG_NAME):
                    dimensions.update(
                        {self.RELAY_NODE_ARG_NAME: self.args.get(self.RELAY_NODE_ARG_NAME)})

                instance = {
                    'name': 'influxdb-relay',
                    'url': 'http://%s:%d/ping' % (host, port),
                    'dimensions': dimensions
                }

                config['http_check'] = {
                    'init_config': None,
                    'instances': [instance]
                }
            else:
                LOG.warning('\tinfluxdb-relay[http] is enabled but nothing '
                            'could be found listening at %d port. '
                            'It might have happened that process '
                            'was just killed and hence port %d '
                            'was released.', port, port)

        return config

    def dependencies_installed(self):
        return importutils.try_import('toml', False)

    @staticmethod
    def _explode_bind_address(http_conf):
        bind_address = http_conf['bind-addr']
        path, port = bind_address.split(':')

        if not path:
            path = InfluxDBRelay.DEFAULTS['bind_address']
        if not port:
            port = InfluxDBRelay.DEFAULTS['bind_port']

        return path, int(port)

    @staticmethod
    def _load_config(config_file):
        """Loads toml configuration from specified path.

        Method loads configuration from specified `path`
        and parses it with :py:class:`configparser.RawConfigParser`

        """
        try:
            return importutils.import_module('toml').load(config_file)
        except Exception as ex:
            LOG.error('Failed to parse %s', config_file)
            LOG.exception(ex)

    @staticmethod
    def _get_config_file(proc):
        """Tries to retrieve config file location.

        influxdb-relay is launched with ```-config```
        flag in cmdline. That fact is used by this method.
        If, by any mean, that switch is not part of
        :py:method:`psutil.Process.cmdline`, method simply
        fallbacks to None

        :param proc: current process, :py:class:`psutil.Process`
        :type proc: :py:class:`psutil.Process`
        :return: config file path or None
        :rtype: str or None

        """
        cmdline = proc.as_dict(attrs=['cmdline'])['cmdline']
        config_flag = '-config'
        if config_flag in cmdline:
            pos = cmdline.index(config_flag)
            return cmdline[pos + 1]
        LOG.warning('%s switch was not found in influxdb-relay cmdline',
                    config_flag)
        return None
