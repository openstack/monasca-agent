import ConfigParser as parser
import logging
import os
import pkg_resources
import re
import six
import string
import cStringIO as cstringio
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import monasca_agent.common.singleton as singleton

DEFAULT_CONFIG_FILE = '/etc/monasca/agent/agent.conf'
DEFAULT_LOG_DIR = '/var/log/monasca/agent'
LOGGING_MAX_BYTES = 5 * 1024 * 1024

log = logging.getLogger(__name__)


class Config(object):
    # Make this a singleton class so we don't get the config every time
    # the class is created
    __metaclass__ = singleton.Singleton

    def __init__(self, configFile=None):
        self._config = None
        if configFile is not None:
            self._configFile = configFile
        elif os.path.exists(DEFAULT_CONFIG_FILE):
            self._configFile = DEFAULT_CONFIG_FILE
        elif os.path.exists(os.getcwd() + '/agent.conf'):
            self._configFile = os.getcwd() + '/agent.conf'
        else:
            log.error('No config file found at {} nor in the working directory.'.format(DEFAULT_CONFIG_FILE))

        self._read_config()

    def get_config(self, sections='Main'):
        """Get the config info."""
        section_list = []
        if isinstance(sections, six.string_types):
            section_list.append(sections)
        elif isinstance(sections, list):
            section_list.extend(sections)
        else:
            log.error('Unknown section: {}'.format(str(sections)))
            return {}

        new_config = {}
        for section in section_list:
            new_config.update(self._config[section])

        return new_config

    def get_version(self):
        return pkg_resources.require("monasca-agent")[0].version

    def _read_config(self):
        """Read in the config file."""

        file_config = parser.SafeConfigParser()
        log.debug("Loading config file from {0}".format(self._configFile))
        file_config.readfp(self._skip_leading_wsp(open(self._configFile)))
        self._config = self._retrieve_sections(file_config)

        # Process and update any special case configuration
        self._parse_config()

    def _retrieve_sections(self, config):
        """Get the section values from the config file."""

        # Define default values for the possible config items
        the_config = {'Main': {'check_freq': 15,
                               'forwarder_url': 'http://localhost:17123',
                               'hostname': None,
                               'dimensions': None,
                               'listen_port': None,
                               'version': self.get_version(),
                               'additional_checksd': os.path.join(os.path.dirname(self._configFile), '/checks_d/'),
                               'system_metrics': None,
                               'ignore_filesystem_types': None,
                               'device_blacklist_re': None,
                               'limit_memory_consumption': None,
                               'skip_ssl_validation': False,
                               'watchdog': True,
                               'use_mount': False,
                               'autorestart': False,
                               'non_local_traffic': False},
                      'Api': {'is_enabled': False,
                              'url': '',
                              'project_name': '',
                              'project_id': '',
                              'project_domain_name': '',
                              'project_domain_id': '',
                              'ca_file': '',
                              'insecure': '',
                              'username': '',
                              'password': '',
                              'use_keystone': True,
                              'keystone_url': '',
                              'max_buffer_size': 1000,
                              'backlog_send_rate': 5},
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
                                  'log_to_event_viewer': False,
                                  'log_to_syslog': False,
                                  'syslog_host': None,
                                  'syslog_port': None}}

        # Load values from configuration file into config file dictionary
        for section in config.sections():
            for option in config.options(section):
                try:
                    option_value = config.get(section, option)
                    if option_value == -1:
                        log.debug("Config option missing: {0}, using default value of {1}".format(option,
                                                                                                  the_config[section][
                                                                                                      option]))
                    else:
                        the_config[section][option] = option_value

                except Exception:
                    log.error("exception on %s!" % option)

        return the_config

    def _skip_leading_wsp(self, file):
        """Works on a file, returns a file-like object"""
        return cstringio.StringIO("\n".join(map(string.strip, file.readlines())))

    def _parse_config(self):
        # Parse_dimensions
        if self._config['Main']['dimensions'] is not None:
            # parse comma separated dimensions into a dimension list
            dimensions = {}
            try:
                dim_list = [dim.split(':') for dim in self._config['Main']['dimensions'].split(',')]
                dimensions.update(dict((key.strip(), value.strip()) for key, value in dim_list))
            except ValueError:
                log.info("Unable to process dimensions.")
                dimensions = {}
            self._config['Main']['dimensions'] = dimensions

        # Parse system metrics
        if self._config['Main']['system_metrics']:
            # parse comma separated system metrics into a metrics list
            try:
                metrics_list = [x.strip() for x in self._config['Main']['system_metrics'].split(',')]
            except ValueError:
                log.info("Unable to process system_metrics.")
                metrics_list = []
            self._config['Main']['system_metrics'] = metrics_list

        # Parse device blacklist regular expression
        try:
            filter_device_re = self._config['Main']['device_blacklist_re']
            if filter_device_re:
                self._config['Main']['device_blacklist_re'] = re.compile(filter_device_re)
        except re.error as err:
            log.error('Error processing regular expression {0}'.format(filter_device_re))

        # Parse file system types
        if self._config['Main']['ignore_filesystem_types']:
            # parse comma separated file system types to ignore list
            try:
                file_system_list = [x.strip() for x in self._config['Main']['ignore_filesystem_types'].split(',')]
            except ValueError:
                log.info("Unable to process ignore_filesystem_types.")
                file_system_list = []
            self._config['Main']['ignore_filesystem_types'] = file_system_list

    def get_confd_path(self):
        path = os.path.join(os.path.dirname(self._configFile), 'conf.d')
        if os.path.exists(path):
            return path
        raise PathNotFound(path)

    def check_yaml(self, conf_path):
        f = open(conf_path)
        try:
            check_config = yaml.load(f.read(), Loader=Loader)
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
                    'You need to have at least one instance defined in the YAML file for this check')
            else:
                return check_config
        finally:
            f.close()


def main():
    configuration = Config()
    config = configuration.get_config()
    api_config = configuration.get_config('Api')
    print "Main Configuration: \n {}".format(config)
    print "\nApi Configuration: \n {}".format(api_config)


if __name__ == "__main__":
    main()
