# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
# Copyright 2016 FUJITSU LIMITED

"""Classes for monitoring the monitoring server stack.

    Covering mon-persister, mon-api and mon-thresh.
    Kafka, mysql, vertica and influxdb are covered by other detection plugins. Mon-notification uses statsd.
"""

import logging
import yaml

from six.moves import configparser

import monasca_setup.agent_config
import monasca_setup.detection
from monasca_setup.detection import find_process_cmdline
from monasca_setup.detection import find_process_name
from monasca_setup.detection.utils import watch_process
from monasca_setup.detection.utils import watch_process_by_username

log = logging.getLogger(__name__)

_PYTHON_LANG_MARKERS = 'python', 'gunicorn',
"""List of all strings that if found in process exe
mean that application runs under Python"""
_JAVA_LANG_MARKERS = 'java',

_DEFAULT_API_PORT = 8070
"""Default TCP port which monasca-api process should be available by"""


def _get_impl_lang(process):
    """Return implementation language of the application behind process

    :param process: current process
    :type process: psutil.Process
    :return: implementation lang, either java or python
    :rtype: str

    """
    p_exe = process.exe()
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
        return watch_process_by_username('mon-agent', 'monasca-agent', 'monitoring',
                                         'monasca-agent')

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

        api_process = find_process_cmdline('monasca-api')
        process_found = api_process is not None

        if process_found:
            impl_lang = _get_impl_lang(api_process)
            impl_helper = self._init_impl_helper(impl_lang)

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
            log.error('monasca-api process has not been found. %s'
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

    @staticmethod
    def _init_impl_helper(impl_lang):
        """Returns appropriate helper implementation.

        :param impl_lang: implementation language, either `java` or `python`
        :type impl_lang: str
        :return: implementation helper
        :rtype: Union(_MonAPIJavaHelper,_MonAPIPythonHelper)

        """
        if impl_lang == 'java':
            return _MonAPIJavaHelper()
        else:
            return _MonAPIPythonHelper()


class MonNotification(monasca_setup.detection.Plugin):
    """Detect the Monsaca notification engine and setup some simple checks."""
    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        if find_process_cmdline('monasca-notification') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return."""
        log.info("\tEnabling the Monasca Notification healthcheck")
        return watch_process_by_username('mon-notification', 'monasca-notification', 'monitoring',
                                         'monasca-notification')

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
            impl_helper = self._init_impl_helper(impl_lang)

            if impl_helper is not None:
                impl_helper.load_configuration()

            self._impl_helper = impl_helper
            self.available = True

            log.info('\tmonasca-persister implementation is %s', impl_lang)

        else:
            log.error('monasca-persister process has not been found. %s'
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
    def _init_impl_helper(impl_lang):
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
            return _MonPersisterJavaHelper()
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
                config.merge(watch_process([process], 'monitoring', 'apache-storm', exact_match=False, detailed=False))
        config.merge(watch_process_by_username('storm', 'monasca-thresh', 'monitoring', 'apache-storm'))
        return config

    def dependencies_installed(self):
        return True


def dropwizard_health_check(service, component, url):
    """Setup a dropwizard heathcheck to be watched by the http_check plugin."""
    config = monasca_setup.agent_config.Plugins()
    config['http_check'] = {'init_config': None,
                            'instances': [{'name': "{0}-{1} healthcheck".format(service, component),
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
                                             'dimensions': {'service': service, 'component': component},
                                             'whitelist': whitelist}]}
    return config


class MonInfluxDB(monasca_setup.detection.Plugin):
    """Detect InfluxDB and setup some simple checks."""

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """

        if find_process_name('influxd') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return."""
        log.info("\tEnabling the Monasca InfluxDB check")
        return watch_process(['influxd'], 'monitoring', 'influxd',
                             exact_match=False)

    def dependencies_installed(self):
        return True


class _MonPersisterJavaHelper(object):
    """Encapsulates Java specific configuration for monasca-persister"""

    CONFIG_FILE = '/etc/monasca/persister-config.yml'
    """Default location where plugin expects configuration file"""

    def __init__(self):
        super(_MonPersisterJavaHelper, self).__init__()
        self._cfg = None

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
        in monaca-persister and sets up new metrics to be monitored.

        Note:
            Only if vertica is TSDB in monasca-persister

        """
        database_type = self._cfg['databaseConfiguration']['databaseType']
        if database_type == 'influxdb':
            pass
        elif database_type == 'vertica':
            self._add_vertica_metrics(whitelist)
        else:
            log.warn('Failed finding database type in %s', self.CONFIG_FILE)

    def _collect_internal_metrics(self, whitelist):
        alarm_num_threads = self._cfg['alarmHistoryConfiguration']['numThreads']
        metric_num_threads = self._cfg['metricConfiguration']['numThreads']

        # Dynamic Whitelist
        for idx in range(alarm_num_threads):
            new_thread = {
                "name": "alarm-state-transitions-added-to-batch-counter[{0}]".format(idx),
                "path": "counters/monasca.persister.pipeline.event.AlarmStateTransitionHandler[alarm-state-transition-{0}].alarm-state-transitions-added-to-batch-counter/count".format(idx),
                "type": "rate"
            }
            whitelist.append(new_thread)
        for idx in range(metric_num_threads):
            new_thread = {
                "name": "metrics-added-to-batch-counter[{0}]".format(idx),
                "path": "counters/monasca.persister.pipeline.event.MetricHandler[metric-{0}].metrics-added-to-batch-counter/count".format(idx),
                "type": "rate"
            }
            whitelist.append(new_thread)

    def _add_vertica_metrics(self, whitelist):
        whitelist.extend([
            {
                "name": "monasca.persister.repository.vertica.VerticaMetricRepo.definition-cache-hit-meter",
                "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo.definition-cache-hit-meter/count",
                "type": "rate"
            },
            {
                "name": "monasca.persister.repository.vertica.VerticaMetricRepo.definition-cache-miss-meter",
                "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo.definition-cache-miss-meter/count",
                "type": "rate"
            },
            {
                "name": "monasca.persister.repository.vertica.VerticaMetricRepo.definition-dimension-cache-hit-meter",
                "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo.definition-dimension-cache-hit-meter/count",
                "type": "rate"
            },
            {
                "name": "monasca.persister.repository.vertica.VerticaMetricRepo.definition-dimension-cache-miss-meter",
                "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo.definition-dimension-cache-miss-meter/count",
                "type": "rate"
            },
            {
                "name": "monasca.persister.repository.vertica.VerticaMetricRepo.dimension-cache-hit-meter",
                "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo.dimension-cache-hit-meter/count",
                "type": "rate"
            },
            {
                "name": "monasca.persister.repository.vertica.VerticaMetricRepo.dimension-cache-miss-meter",
                "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo.dimension-cache-miss-meter/count",
                "type": "rate"
            },
            {
                "name": "monasca.persister.repository.vertica.VerticaMetricRepo.measurement-meter",
                "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo.measurement-meter/count",
                "type": "rate"
            }
        ])

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

    def load_configuration(self):
        """Loads java specific configuration.

        Load java specific configuration from:

        * :py:attr:`API_CONFIG_YML`

        :return: True if both configuration files were successfully loaded
        :rtype: bool

        """
        try:
            with open(self.CONFIG_FILE, 'r') as config:
                self._cfg = yaml.safe_load(config.read())
        except Exception as ex:
            log.error('Failed to parse %s', self.CONFIG_FILE)
            log.exception(ex)
            raise ex


class _MonAPIJavaHelper(object):
    """Encapsulates Java specific configuration for monasca-api"""

    CONFIG_FILE = '/etc/monasca/api-config.yml'

    def __init__(self):
        super(_MonAPIJavaHelper, self).__init__()
        self._api_config = None

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
        admin_connector = self._api_config['server']['adminConnectors'][0]

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

        api_config = getattr(self, '_api_config', None)
        if api_config is None:
            return False

        hibernate_cfg = self._api_config.get('hibernate', None)
        if hibernate_cfg is None:
            return False

        return hibernate_cfg.get('supportEnabled', False)

    def load_configuration(self):
        """Loads java specific configuration.

        Load java specific configuration from:

        * :py:attr:`API_CONFIG_YML`

        :return: True if both configuration files were successfully loaded
        :rtype: bool

        """
        try:
            with open(self.CONFIG_FILE, 'r') as config:
                self._api_config = yaml.safe_load(config.read())
        except Exception as ex:
            log.error('Failed to parse %s', self.CONFIG_FILE)
            log.exception(ex)
            raise ex

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
        if self._api_config is None:
            return _DEFAULT_API_PORT
        try:
            return self._api_config['server']['applicationConnectors'][0]['port']
        except Exception as ex:
            log.error('Failed to read api port from '
                      '/etc/monasca/api-config.yml')
            log.exception(ex)
            return _DEFAULT_API_PORT


class _MonAPIPythonHelper(object):
    """Encapsulates Python specific configuration for monasca-api"""

    CONFIG_FILE = '/etc/monasca/api-config.ini'

    def __init__(self):
        super(_MonAPIPythonHelper, self).__init__()
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
        cp = configparser.RawConfigParser()
        try:
            cp.readfp(open(self.CONFIG_FILE, 'r'))
            self._paste_config = cp
        except Exception as ex:
            log.error('Failed to parse %s', self.CONFIG_FILE)
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
