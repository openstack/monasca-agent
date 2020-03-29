# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
# Copyright 2016 FUJITSU LIMITED
# Copyright 2017 SUSE Linux GmbH
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

"""Classes for monitoring the monitoring server stack.

    Covering mon-persister, mon-api and mon-thresh.
    Kafka, mysql, vertica and influxdb are covered by other detection plugins. Mon-notification
    uses statsd.
"""

import logging
import re
import yaml

from six.moves import configparser

import monasca_setup.agent_config
import monasca_setup.detection
from monasca_setup.detection import find_process_cmdline
from monasca_setup.detection.utils import get_agent_username
from monasca_setup.detection.utils import watch_process
from monasca_setup.detection.utils import watch_process_by_username

log = logging.getLogger(__name__)

_APACHE_MARKERS = 'httpd', 'apache',
"""List of all strings in process command line that indicate application
runs in Apache/mod_wsgi"""
_PYTHON_LANG_MARKERS = ('python', 'gunicorn') + _APACHE_MARKERS
"""List of all strings that if found in process exe
mean that application runs under Python"""
_JAVA_LANG_MARKERS = 'java',
"""List of all strings that if found in process exe
mean that application runs under Java"""

_DEFAULT_API_PORT = 8070
"""Default TCP port which monasca-api process should be available by"""


def _get_impl_lang(process):
    """Return implementation language of the application behind process

    :param process: current process
    :type process: psutil.Process
    :return: implementation lang, either java or python
    :rtype: str

    """
    p_exe = process.as_dict(['exe'])['exe']
    for lm in _PYTHON_LANG_MARKERS:
        if lm in p_exe:
            return 'python'
    for lm in _JAVA_LANG_MARKERS:
        if lm in p_exe:
            return 'java'
    raise Exception(('Cannot determine language '
                     'implementation from process exe %s') % p_exe)


class MonAgent(monasca_setup.detection.Plugin):
    """Detect the Monsaca agent engine and setup some simple checks."""

    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        self.available = True
        agent_process_list = ['monasca-collector', 'monasca-forwarder',
                              'monasca-statsd']
        for process in agent_process_list:
            if find_process_cmdline(process) is None:
                self.available = False
                return

    def build_config(self):
        """Build the config as a Plugins object and return."""
        log.info("\tEnabling the Monasca Agent process check")
        return watch_process_by_username(get_agent_username(), 'monasca-agent',
                                         'monitoring', 'monasca-agent')

    def dependencies_installed(self):
        return True


class MonAPI(monasca_setup.detection.Plugin):
    """Detect mon_api and setup monitoring."""

    PARTIAL_ERR_MSG = 'Plugin for monasca-api will not be configured.'

    def _detect(self):
        """Detects if monasca-api runs in the system

        Method distinguishes between Java and Python implementation
        hence provides different agent's configuration.

        """

        def check_port():
            for conn in api_process.connections('inet'):
                if conn.laddr[1] == api_port:
                    return True
            return False

        def correct_apache_listener(process):
            """Sets api_process to the parent httpd process.

            Method evaluates if process executable is correlated
            with apache-mod_wsgi. If so, retrieves parent process.
            Otherwise returns None

            :param process: current process
            :type process: psutil.Process
            :returns: parent process or None
            :rtype: (psutil.Process, None)

            """

            p_exe = process.as_dict(['exe'])['exe']
            for m in _APACHE_MARKERS:
                if m in p_exe:
                    return process.parent()
            return None

        api_process = find_process_cmdline('monasca-api')
        process_found = api_process is not None

        if process_found:
            impl_lang = _get_impl_lang(api_process)
            if impl_lang == 'python':
                apache_process = correct_apache_listener(api_process)
                if apache_process:
                    log.info('\tmonasca-api runs under Apache WSGI')
                    api_process = apache_process

            impl_helper = self._init_impl_helper(api_process.as_dict(['cmdline'])['cmdline'],
                                                 impl_lang)
            impl_helper.load_configuration()

            api_port = impl_helper.get_bound_port()
            port_taken = check_port()

            if not port_taken:
                log.error('monasca-api is not listening on port %d. %s'
                          % (api_port, self.PARTIAL_ERR_MSG))
                return

            log.info('\tmonasca-api implementation is %s', impl_lang)

            self.available = port_taken
            self._impl_helper = impl_helper
        else:
            log.warning('monasca-api process has not been found. %s'
                        % self.PARTIAL_ERR_MSG)

    def build_config(self):
        """Build the config as a Plugins object and return."""
        config = monasca_setup.agent_config.Plugins()

        log.info("\tEnabling the monasca-api process check")
        config.merge(watch_process(
            search_strings=['monasca-api'],
            service='monitoring',
            component='monasca-api',
            exact_match=False
        ))
        impl_config = self._impl_helper.build_config()
        if impl_config:
            config.merge(impl_config)

        return config

    def dependencies_installed(self):
        return True

    def _init_impl_helper(self, cmdline, impl_lang):
        """Returns appropriate helper implementation.

        :param impl_lang: implementation language, either `java` or `python`
        :type impl_lang: str
        :return: implementation helper
        :rtype: Union(_MonAPIJavaHelper,_MonAPIPythonHelper)

        """
        if impl_lang == 'java':
            return _MonAPIJavaHelper(cmdline=cmdline)
        else:
            return _MonAPIPythonHelper(cmdline=cmdline, args=self.args)


class MonNotification(monasca_setup.detection.Plugin):
    """Detect the Monsaca notification engine and setup some simple checks."""

    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        if find_process_cmdline('monasca-notification') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return."""
        log.info("\tEnabling the Monasca Notification healthcheck")
        notification_process = find_process_cmdline('monasca-notification')
        notification_user = notification_process.as_dict(['username'])['username']
        return watch_process_by_username(notification_user, 'monasca-notification',
                                         'monitoring', 'monasca-notification')

    def dependencies_installed(self):
        return True


class MonPersister(monasca_setup.detection.Plugin):
    """Detect mon_persister and setup monitoring."""

    PARTIAL_ERR_MSG = 'Plugin for monasca-persister will not be configured.'

    def _detect(self):
        """Detects if monasca-persister runs in the system

        Method distinguishes between Java and Python implementation
        hence provides different agent's configuration.

        """
        p_process = find_process_cmdline('monasca-persister')
        process_found = p_process is not None

        if process_found:
            impl_lang = _get_impl_lang(p_process)
            impl_helper = self._init_impl_helper(
                p_process.as_dict(['cmdline'])['cmdline'],
                impl_lang
            )

            if impl_helper is not None:
                impl_helper.load_configuration()

            self._impl_helper = impl_helper
            self.available = True

            log.info('\tmonasca-persister implementation is %s', impl_lang)

        else:
            log.info('monasca-persister process has not been found. %s'
                     % self.PARTIAL_ERR_MSG)

    def build_config(self):
        """Build the config as a Plugins object and return."""
        config = monasca_setup.agent_config.Plugins()

        log.info("\tEnabling the Monasca persister process check")
        config.merge(watch_process(
            search_strings=['monasca-persister'],
            service='monitoring',
            component='monasca-persister',
            exact_match=False
        ))
        if self._impl_helper is not None:
            impl_config = self._impl_helper.build_config()
            if impl_config:
                config.merge(impl_config)

        return config

    def dependencies_installed(self):
        return True

    @staticmethod
    def _init_impl_helper(cmdline, impl_lang):
        """Returns appropriate helper implementation.

        Note:

            This method returns the helper only for Java.
            Python implementation comes with no extra setup.

        :param impl_lang: implementation language, either `java` or `python`
        :type impl_lang: str
        :return: implementation helper
        :rtype:_MonPersisterJavaHelper

        """
        if impl_lang == 'java':
            return _MonPersisterJavaHelper(cmdline=cmdline)
        return None


class MonThresh(monasca_setup.detection.Plugin):
    """Detect the running mon-thresh and monitor."""

    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        # The node will be running either nimbus or supervisor or both
        self.available = (find_process_cmdline('storm.daemon.nimbus') is not None or
                          find_process_cmdline('storm.daemon.supervisor') is not None)

    def build_config(self):
        """Build the config as a Plugins object and return."""
        log.info("\tWatching the mon-thresh process.")
        config = monasca_setup.agent_config.Plugins()
        for process in ['storm.daemon.nimbus', 'storm.daemon.supervisor', 'storm.daemon.worker']:
            if find_process_cmdline(process) is not None:
                config.merge(
                    watch_process(
                        [process],
                        'monitoring',
                        'apache-storm',
                        exact_match=False,
                        detailed=False))
        config.merge(
            watch_process_by_username(
                'storm',
                'monasca-thresh',
                'monitoring',
                'apache-storm'))
        return config

    def dependencies_installed(self):
        return True


def dropwizard_health_check(service, component, url):
    """Setup a dropwizard heathcheck to be watched by the http_check plugin."""
    config = monasca_setup.agent_config.Plugins()
    config['http_check'] = {'init_config': None,
                            'instances': [
                                {'name': "{0}-{1} healthcheck".format(service, component),
                                 'url': url,
                                 'timeout': 5,
                                 'include_content': False,
                                 'dimensions': {'service': service, 'component': component}}]}
    return config


def dropwizard_metrics(service, component, url, whitelist):
    """Setup a dropwizard metrics check"""
    config = monasca_setup.agent_config.Plugins()
    config['http_metrics'] = {'init_config': None,
                              'instances': [{'name': "{0}-{1} metrics".format(service, component),
                                             'url': url,
                                             'timeout': 5,
                                             'dimensions': {'service': service,
                                                            'component': component},
                                             'whitelist': whitelist}]}
    return config


class _DropwizardJavaHelper(object):
    """Mixing to locate configuration file for DropWizard app

    Class utilizes process of search the configuartion file
    for:

    * monasca-api [**Java**]
    * monasca-persister [**Java**]
    """

    YAML_PATTERN = re.compile(r'.*\.ya?ml', re.IGNORECASE)

    def __init__(self, cmdline=None):
        self._cmdline = cmdline

    def load_configuration(self):
        """Loads java specific configuration.

        Load java specific configuration from:

        * :py:attr:`DEFAULT_CONFIG_FILE`

        :return: True if both configuration files were successfully loaded
        :rtype: bool

        """
        try:
            config_file = self._get_config_file()
            self._read_config_file(config_file)
        except Exception as ex:
            log.error('Failed to parse %s', config_file)
            log.exception(ex)
            raise ex

    def _find_config_file_in_cmdline(self, cmdline):
        # note(trebskit) file should be mentioned
        # somewhere in the end of cmdline
        for item in cmdline[::-1]:
            if self.YAML_PATTERN.match(item):
                return item
        return None

    def _read_config_file(self, config_file):
        with open(config_file, 'r') as config:
            self._cfg = yaml.safe_load(config.read())

    def _get_config_file(self):
        if self._cmdline:
            config_file = self._find_config_file_in_cmdline(
                cmdline=self._cmdline
            )
            if config_file:
                log.debug('\tFound %s for java configuration from CLI',
                          config_file)
                return config_file

        config_file = self.DEFAULT_CONFIG_FILE
        log.debug('\tAssuming default configuration file=%s', config_file)
        return config_file


class _MonPersisterJavaHelper(_DropwizardJavaHelper):
    """Encapsulates Java specific configuration for monasca-persister"""

    DEFAULT_CONFIG_FILE = '/etc/monasca/persister-config.yml'
    """Default location where plugin expects configuration file"""

    def build_config(self):
        config = monasca_setup.agent_config.Plugins()
        metrics = self._collect_metrics()
        self._monitor_endpoints(config, metrics)
        return config

    def _collect_metrics(self):
        """Collects all the metrics .

        Methods will return list of all metrics that will
        later be used in
        :py:mod:`monasca_agent.collector.checks_d.http_metrics` to query
        admin endpoint of monasca-persister.

        Following group of metrics are examined:

        * JVM metrics
        * DB metrics ( see also :py:meth:`._collect_db_metrics` )
        * Internal metrics ( see also :py:meth:`._collect_internal_metrics` )

        :return: list of metrics
        :rtype: list

        """
        log.info("\tEnabling the monasca-persister metrics")

        whitelist = [
            {
                "name": "jvm.memory.total.max",
                "path": "gauges/jvm.memory.total.max/value",
                "type": "gauge"
            },
            {
                "name": "jvm.memory.total.used",
                "path": "gauges/jvm.memory.total.used/value",
                "type": "gauge"
            }
        ]

        self._collect_db_metrics(whitelist)
        self._collect_internal_metrics(whitelist)

        return whitelist

    def _collect_db_metrics(self, whitelist):
        """Collects DB specific metrics.

        Method retrieves which time-series database is used
        in monasca-persister and sets up new metrics to be monitored.

        Note:
            Only if vertica is TSDB in monasca-persister

        """
        database_type = self._cfg['databaseConfiguration']['databaseType']
        if database_type == 'influxdb':
            pass
        elif database_type == 'vertica':
            self._add_vertica_metrics(whitelist)
        else:
            log.warn('Failed finding database type in %s', self.DEFAULT_CONFIG_FILE)

    def _collect_internal_metrics(self, whitelist):
        alarm_num_threads = self._cfg['alarmHistoryConfiguration']['numThreads']
        metric_num_threads = self._cfg['metricConfiguration']['numThreads']

        # Dynamic Whitelist
        for idx in range(alarm_num_threads):
            new_thread = {
                "name": "alarm-state-transitions-added-to-batch-counter[{0}]".format(idx),
                "path": "counters/monasca.persister.pipeline.event."
                        "AlarmStateTransitionHandler[alarm-state-transition-{0}]."
                        "alarm-state-transitions-added-to-batch-counter/count".format(idx),
                "type": "rate"}
            whitelist.append(new_thread)
        for idx in range(metric_num_threads):
            new_thread = {
                "name": "metrics-added-to-batch-counter[{0}]".format(idx),
                "path": "counters/monasca.persister.pipeline.event.MetricHandler[metric-{0}]."
                        "metrics-added-to-batch-counter/count".format(idx),
                "type": "rate"}
            whitelist.append(new_thread)

    def _add_vertica_metrics(self, whitelist):
        whitelist.extend(
            [{"name": "monasca.persister.repository.vertica.VerticaMetricRepo."
                      "definition-cache-hit-meter",
              "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo."
                      "definition-cache-hit-meter/count",
              "type": "rate"},
             {"name": "monasca.persister.repository.vertica.VerticaMetricRepo."
                      "definition-cache-miss-meter",
              "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo."
                      "definition-cache-miss-meter/count",
              "type": "rate"},
             {"name": "monasca.persister.repository.vertica.VerticaMetricRepo."
                      "definition-dimension-cache-hit-meter",
              "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo."
                      "definition-dimension-cache-hit-meter/count",
              "type": "rate"},
             {"name": "monasca.persister.repository.vertica.VerticaMetricRepo."
                      "definition-dimension-cache-miss-meter",
              "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo."
                      "definition-dimension-cache-miss-meter/count",
              "type": "rate"},
             {"name": "monasca.persister.repository.vertica.VerticaMetricRepo."
                      "dimension-cache-hit-meter",
              "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo."
                      "dimension-cache-hit-meter/count",
              "type": "rate"},
             {"name": "monasca.persister.repository.vertica.VerticaMetricRepo."
                      "dimension-cache-miss-meter",
              "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo."
                      "dimension-cache-miss-meter/count",
              "type": "rate"},
             {"name": "monasca.persister.repository.vertica.VerticaMetricRepo.measurement-meter",
              "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo."
                      "measurement-meter/count",
              "type": "rate"}])

    def _monitor_endpoints(self, config, metrics):
        admin_connector = self._cfg['server']['adminConnectors'][0]

        try:
            admin_endpoint_type = admin_connector['type']
        except Exception:
            admin_endpoint_type = "http"
        try:
            admin_endpoint_port = admin_connector['port']
        except Exception:
            admin_endpoint_port = 8091

        log.info("\tEnabling the Monasca persister healthcheck")
        config.merge(
            dropwizard_health_check(
                'monitoring',
                'monasca-persister',
                '{0}://localhost:{1}/healthcheck'.format(admin_endpoint_type,
                                                         admin_endpoint_port)))

        log.info("\tEnabling the Monasca persister metrics")
        config.merge(
            dropwizard_metrics(
                'monitoring',
                'monasca-persister',
                '{0}://localhost:{1}/metrics'.format(admin_endpoint_type,
                                                     admin_endpoint_port),
                metrics))


class _MonAPIJavaHelper(_DropwizardJavaHelper):
    """Encapsulates Java specific configuration for monasca-api"""

    DEFAULT_CONFIG_FILE = '/etc/monasca/api-config.yml'

    def build_config(self):
        """Builds monitoring configuration for monasca-api Java flavour.

        Method configures additional checks that are specific for
        Java implementation of monasca-api.

        List of checks:

        * HttpCheck, :py:mod:`monasca_agent.collector.checks_d.http_check`
        * HttpMetrics, :py:mod:`monasca_agent.collector.checks_d.http_metrics`

        """
        config = monasca_setup.agent_config.Plugins()

        log.info("\tEnabling the Monasca api metrics")
        whitelist = [
            {
                "name": "jvm.memory.total.max",
                "path": "gauges/jvm.memory.total.max/value",
                "type": "gauge"
            },
            {
                "name": "jvm.memory.total.used",
                "path": "gauges/jvm.memory.total.used/value",
                "type": "gauge"
            },
            {
                "name": "metrics.published",
                "path": "meters/monasca.api.app.MetricService.metrics.published/count",
                "type": "rate"
            }
        ]

        if not self._is_hibernate_on():
            # if hibernate is not used, it is mysql with DBI
            # for that case having below entries makes sense
            log.debug(
                'monasca-api has not enabled Hibernate, adding DBI metrics')
            whitelist.extend([
                {
                    "name": "raw-sql.time.avg",
                    "path": "timers/org.skife.jdbi.v2.DBI.raw-sql/mean",
                    "type": "gauge"
                },
                {
                    "name": "raw-sql.time.max",
                    "path": "timers/org.skife.jdbi.v2.DBI.raw-sql/max",
                    "type": "gauge"
                }
            ])

        self._monitor_endpoints(config, whitelist)

        return config

    def _monitor_endpoints(self, config, metrics):
        admin_connector = self._cfg['server']['adminConnectors'][0]

        try:
            admin_endpoint_type = admin_connector['type']
        except Exception:
            admin_endpoint_type = "http"
        try:
            admin_endpoint_port = admin_connector['port']
        except Exception:
            admin_endpoint_port = 8081

        healthcheck_url = '{0}://localhost:{1}/healthcheck'.format(
            admin_endpoint_type, admin_endpoint_port)
        metric_url = '{0}://localhost:{1}/metrics'.format(
            admin_endpoint_type, admin_endpoint_port)

        log.info("\tEnabling the monasca-api healthcheck")
        config.merge(dropwizard_health_check('monitoring', 'monasca-api',
                                             healthcheck_url))
        log.info("\tEnabling the monasca-api metrics")
        config.merge(dropwizard_metrics('monitoring', 'monasca-api',
                                        metric_url, metrics))

    def _is_hibernate_on(self):
        # check if api_config has been declared in __init__
        # if not it means that configuration file was not found
        # or monasca-api Python implementation is running

        cfg = getattr(self, '_cfg', None)
        if cfg is None:
            return False

        hibernate_cfg = cfg.get('hibernate', None)
        if hibernate_cfg is None:
            return False

        return hibernate_cfg.get('supportEnabled', False)

    def get_bound_port(self):
        """Returns port API is listening on.

        Method tries to read port from the '/etc/monasca/api-config.yml'
        file. In case if:

        * file was not found in specified location
        * file could be read from the file system
        * file was changed and assumed location of port changed

        code rollbacks to :py:const:`_DEFAULT_API_PORT`

        :return: TCP port api is listening on
        :rtype: int

        """
        if self._cfg is None:
            return _DEFAULT_API_PORT
        try:
            return self._cfg['server']['applicationConnectors'][0]['port']
        except Exception as ex:
            log.error('Failed to read api port from configuration file')
            log.exception(ex)
            return _DEFAULT_API_PORT


class _MonAPIPythonHelper(object):
    """Encapsulates Python specific configuration for monasca-api"""

    DEFAULT_CONFIG_FILE = '/etc/monasca/api-config.ini'
    PASTE_CLI_OPTS = '--paste', '--paster',
    """Possible flags passed to gunicorn processed,
    pointing at paste file"""

    def __init__(self, cmdline=None, args=None):
        super(_MonAPIPythonHelper, self).__init__()
        self._cmdline = cmdline
        self._args = args
        self._paste_config = None

    def build_config(self):
        # note(trebskit) intentionally left empty because gunicorn check
        # seems to have some serious issues with monitoring gunicorn process
        # see https://bugs.launchpad.net/monasca/+bug/1646481
        return None

    def load_configuration(self):
        """Loads INI file from specified path.

        Method loads configuration from specified `path`
        and parses it with :py:class:`configparser.RawConfigParser`

        """
        try:
            config_file = self._get_config_file()
            self._paste_config = self._read_config_file(config_file)
        except Exception as ex:
            log.error('Failed to parse %s', config_file)
            log.exception(ex)
            raise ex

    def get_bound_port(self):
        """Returns port API is listening on.

        Method tries to read port from the '/etc/monasca/api-config.ini'
        file. In case if:

        * file was not found in specified location
        * file could be read from the file system
        * file was changed and assumed location of port changed

        code rollbacks to :py:const:`_DEFAULT_API_PORT`

        :return: TCP port api is listening on
        :rtype: int

        """
        if not self._paste_config:
            return _DEFAULT_API_PORT
        return self._paste_config.getint('server:main', 'port')

    def _read_config_file(self, config_file):
        cp = configparser.RawConfigParser()
        return cp.readfp(open(config_file, 'r'))

    def _get_config_file(self):
        """Method gets configuration file of Python monasca-api.

        Method tries to examine following locations:

        * cmdline of process (looking for either
            of :py:attr:`_MonAPIPythonHelper.PASTE_CLI_OPTS`)
        * this plugin args

        loooking for location of configuration file

        :param args: plugin arguments
        :type args: dict

        """

        if self._cmdline:
            # we're interested in PASTE_CLI_OPTS
            for paste in self.PASTE_CLI_OPTS:
                if paste in self._cmdline:
                    pos = self._cmdline.index(paste)
                    flag = self._cmdline[pos]
                    config_file = self._cmdline[pos + 1]
                    if config_file:
                        log.debug(('\tFound %s=%s for python configuration '
                                   'from CLI'),
                                  flag, config_file)
                        return config_file
                else:
                    log.warn(('\tCannot determine neither %s from process'
                              'cmdline'), self.PASTE_CLI_OPTS)

        if self._args and 'paste-file' in self._args:
            # check if args mentions config file param
            config_file = self._args.get('paste-file', None)
            log.debug(('\tFound paste-file=%s for python configuration '
                       'passed as plugin argument'), config_file)
            return config_file

        config_file = self.DEFAULT_CONFIG_FILE
        log.debug('\tAssuming default paste_file=%s', config_file)

        return config_file
