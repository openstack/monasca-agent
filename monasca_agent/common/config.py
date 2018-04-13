# (C) Copyright 2015-2018 Hewlett Packard Enterprise Development LP
# Copyright 2017 Fujitsu LIMITED
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
import six
import yaml

from monasca_agent.common import exceptions
from monasca_agent.common import singleton
from monasca_agent import version

DEFAULT_CONFIG_FILE = '/etc/monasca/agent/agent.yaml'
DEFAULT_LOG_DIR = '/var/log/monasca/agent'
LOGGING_MAX_BYTES = 5 * 1024 * 1024

log = logging.getLogger(__name__)


# Make this a singleton class so we don't get the config every time
# the class is created
@six.add_metaclass(singleton.Singleton)
class Config(object):

    def __init__(self, configFile=None):
        # importing it here, in order to avoid a circular import
        # as monasca_agent.common.util imports this module.
        from monasca_agent.common import util

        options, args = util.get_parsed_args()
        if configFile is not None:
            self._configFile = configFile
        elif options.config_file is not None:
            self._configFile = options.config_file
        elif os.path.exists(DEFAULT_CONFIG_FILE):
            self._configFile = DEFAULT_CONFIG_FILE
        elif os.path.exists(os.getcwd() + '/agent.yaml'):
            self._configFile = os.getcwd() + '/agent.yaml'
        else:
            error_msg = 'No config file found at {0} nor in the working directory.'.format(
                DEFAULT_CONFIG_FILE)
            log.error(error_msg)
            raise IOError(error_msg)

        # Define default values for the possible config items
        self._config = {'Main': {'check_freq': 15,
                                 'forwarder_url': 'http://localhost:17123',
                                 'hostname': None,
                                 'dimensions': None,
                                 'listen_port': None,
                                 'version': self.get_version(),
                                 'additional_checksd': '/usr/lib/monasca/agent/custom_checks.d',
                                 'limit_memory_consumption': None,
                                 'skip_ssl_validation': False,
                                 'autorestart': True,
                                 'non_local_traffic': False,
                                 'sub_collection_warn': 6,
                                 'collector_restart_interval': 24},
                        'Api': {'is_enabled': False,
                                'url': '',
                                'project_name': '',
                                'project_id': '',
                                'project_domain_name': '',
                                'project_domain_id': '',
                                'ca_file': '',
                                'insecure': False,
                                'username': '',
                                'password': '',
                                'use_keystone': True,
                                'keystone_timeout': 20,
                                'keystone_url': '',
                                'max_buffer_size': 1000,
                                'max_measurement_buffer_size': -1,
                                'write_timeout': 10,
                                'backlog_send_rate': 5,
                                'max_batch_size': 0},
                        'Statsd': {'recent_point_threshold': None,
                                   'monasca_statsd_interval': 20,
                                   'monasca_statsd_forward_host': None,
                                   'monasca_statsd_forward_port': 8125,
                                   'monasca_statsd_port': 8125},
                        'Logging': {'disable_file_logging': False,
                                    'log_level': None,
                                    'collector_log_file': DEFAULT_LOG_DIR + '/collector.log',
                                    'forwarder_log_file': DEFAULT_LOG_DIR + '/forwarder.log',
                                    'statsd_log_file': DEFAULT_LOG_DIR + '/statsd.log',
                                    'jmxfetch_log_file': DEFAULT_LOG_DIR + '/jmxfetch.log',
                                    'enable_logrotate': True,
                                    'log_to_event_viewer': False,
                                    'log_to_syslog': False,
                                    'syslog_host': None,
                                    'syslog_port': None}}

        self._read_config()

    def get_config(self, sections='Main'):
        """Get the config info."""
        section_list = []
        if isinstance(sections, six.string_types):
            section_list.append(sections)
        elif isinstance(sections, list):
            section_list.extend(sections)
        else:
            log.error('Unknown section: {0}'.format(str(sections)))
            return {}

        new_config = {}
        for section in section_list:
            new_config.update(self._config[section])

        return new_config

    def get_version(self):
        return version.version_string

    def _read_config(self):
        """Read in the config file."""
        try:
            with open(self._configFile, 'r') as f:
                log.debug('Loading config file from {0}'.format(self._configFile))
                config = yaml.safe_load(f.read())
                [self._config[section].update(config[section]) for section in config.keys()]
        except Exception as e:
            log.exception('Error loading config file from {0}'.format(self._configFile))
            raise e

    def get_confd_path(self):
        path = os.path.join(os.path.dirname(self._configFile), 'conf.d')
        if os.path.exists(path):
            return path
        raise exceptions.PathNotFound(path)

    def check_yaml(self, conf_path):
        f = open(conf_path)
        try:
            check_config = yaml.safe_load(f.read())
            assert 'init_config' in check_config, "No 'init_config' section found"
            assert 'instances' in check_config, "No 'instances' section found"

            valid_instances = True
            if check_config['instances'] is None or not isinstance(check_config['instances'], list):
                valid_instances = False
            else:
                for i in check_config['instances']:
                    if not isinstance(i, dict):
                        valid_instances = False
                        break
            if not valid_instances:
                raise Exception(
                    'You need to have at least one instance defined'
                    'in the YAML file for this check')
            else:
                return check_config
        finally:
            f.close()


def main():
    configuration = Config()
    config = configuration.get_config()
    api_config = configuration.get_config('Api')
    statsd_config = configuration.get_config('Statsd')
    logging_config = configuration.get_config('Logging')
    print("Main Configuration: \n {0}".format(config))
    print("\nApi Configuration: \n {0}".format(api_config))
    print("\nStatsd Configuration: \n {0}".format(statsd_config))
    print("\nLogging Configuration: \n {0}".format(logging_config))


if __name__ == "__main__":
    logging.basicConfig()
    main()
