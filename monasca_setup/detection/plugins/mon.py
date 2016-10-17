# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP

"""Classes for monitoring the monitoring server stack.

    Covering mon-persister, mon-api and mon-thresh.
    Kafka, mysql, vertica and influxdb are covered by other detection plugins. Mon-notification uses statsd.
"""

import logging
import yaml

import monasca_setup.agent_config
import monasca_setup.detection
from monasca_setup.detection import find_process_cmdline
from monasca_setup.detection import find_process_name
from monasca_setup.detection import watch_process
from monasca_setup.detection import watch_process_by_username

log = logging.getLogger(__name__)


class MonAgent(monasca_setup.detection.Plugin):
    """Detect the Monsaca agent engine and setup some simple checks."""
    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        self.available = True
        agent_process_list = ['monasca-collector', 'monasca-forwarder', 'monasca-statsd']
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
    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        monasca_api = monasca_setup.detection.find_process_cmdline('monasca-api')
        if monasca_api is not None:
            # monasca-api can show up in urls and be an arg to this setup program, check port also
            # Find the right port from the config, this is specific to the Java version
            try:
                with open('/etc/monasca/api-config.yml', 'r') as config:
                    self.api_config = yaml.safe_load(config.read())
                api_port = self.api_config['server']['applicationConnectors'][0]['port']
            except Exception:
                api_port = 8070
                log.warn('Failed parsing /etc/monasca/api-config.yml, defaulting api port to {0}'.format(api_port))
            for conn in monasca_api.connections('inet'):
                if conn.laddr[1] == api_port:
                    self.available = True
                    return

    def build_config(self):
        """Build the config as a Plugins object and return."""
        config = monasca_setup.agent_config.Plugins()

        log.info("\tEnabling the Monasca api process check")
        config.merge(watch_process(['monasca-api'], 'monitoring', 'monasca-api', exact_match=False))

        log.info("\tEnabling the Monasca api healthcheck")
        config.merge(dropwizard_health_check('monitoring', 'monasca-api', 'http://localhost:8081/healthcheck'))

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
            log.debug('MonApi has not enabled Hibernate, adding DBI metrics')
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

        config.merge(dropwizard_metrics('monitoring',
                                        'monasca-api',
                                        'http://localhost:8081/metrics',
                                        whitelist))

        return config

    def dependencies_installed(self):
        return True

    def _is_hibernate_on(self):
        # check if api_config has been declared in __init__
        # if not it means that configuration file was not found
        # or monasca-api Python implementation is running

        api_config = getattr(self, 'api_config', None)
        if api_config is None:
            return False

        hibernate_cfg = self.api_config.get('hibernate', None)
        if hibernate_cfg is None:
            return False

        return hibernate_cfg.get('supportEnabled', False)


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
    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        if find_process_cmdline('monasca-persister') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return."""
        """Read persister-config.yml file to find the exact numThreads."""
        try:
            with open('/etc/monasca/persister-config.yml', 'r') as config:
                self.persister_config = yaml.safe_load(config.read())
        except Exception:
            log.exception('Failed parsing /etc/monasca/persister-config.yml')
            self.available = False
            return

        alarm_num_threads = self.persister_config['alarmHistoryConfiguration']['numThreads']
        metric_num_threads = self.persister_config['metricConfiguration']['numThreads']

        database_type = self.persister_config['databaseConfiguration']['databaseType']

        config = monasca_setup.agent_config.Plugins()

        log.info("\tEnabling the Monasca persister process check")
        config.merge(watch_process(['monasca-persister'], 'monitoring', 'monasca-persister', exact_match=False))

        adminConnector = self.persister_config['server']['adminConnectors'][0]
        try:
            admin_endpoint_type = adminConnector['type']
        except Exception:
            admin_endpoint_type = "http"

        try:
            admin_endpoint_port = adminConnector['port']
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
        whitelist = [
            {
                "name": "jvm.memory.total.max",
                "path": "gauges/jvm.memory.total.max/value",
                "type": "gauge"},
            {
                "name": "jvm.memory.total.used",
                "path": "gauges/jvm.memory.total.used/value",
                "type": "gauge"}
        ]

        # Generate initial whitelist based on the database type
        if database_type == 'influxdb':
            pass
        elif database_type == 'vertica':
            whitelist.extend([
                {
                    "name": "monasca.persister.repository.vertica.VerticaMetricRepo.definition-cache-hit-meter",
                    "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo.definition-cache-hit-meter/count",
                    "type": "rate"},
                {
                    "name": "monasca.persister.repository.vertica.VerticaMetricRepo.definition-cache-miss-meter",
                    "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo.definition-cache-miss-meter/count",
                    "type": "rate"},
                {
                    "name": "monasca.persister.repository.vertica.VerticaMetricRepo.definition-dimension-cache-hit-meter",
                    "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo.definition-dimension-cache-hit-meter/count",
                    "type": "rate"},
                {
                    "name": "monasca.persister.repository.vertica.VerticaMetricRepo.definition-dimension-cache-miss-meter",
                    "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo.definition-dimension-cache-miss-meter/count",
                    "type": "rate"},
                {
                    "name": "monasca.persister.repository.vertica.VerticaMetricRepo.dimension-cache-hit-meter",
                    "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo.dimension-cache-hit-meter/count",
                    "type": "rate"},
                {
                    "name": "monasca.persister.repository.vertica.VerticaMetricRepo.dimension-cache-miss-meter",
                    "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo.dimension-cache-miss-meter/count",
                    "type": "rate"},
                {
                    "name": "monasca.persister.repository.vertica.VerticaMetricRepo.measurement-meter",
                    "path": "meters/monasca.persister.repository.vertica.VerticaMetricRepo.measurement-meter/count",
                    "type": "rate"}
            ])
        else:
            log.warn('Failed finding database type in /etc/monasca/persister-config.yml')

        # Dynamic Whitelist
        for idx in range(alarm_num_threads):
            new_thread = {"name": "alarm-state-transitions-added-to-batch-counter[{0}]".format(idx),
                          "path": "counters/monasca.persister.pipeline.event.AlarmStateTransitionHandler[alarm-state-transition-{0}].alarm-state-transitions-added-to-batch-counter/count".format(idx),
                          "type": "rate"
                          }
            whitelist.append(new_thread)

        for idx in range(metric_num_threads):
            new_thread = {"name": "metrics-added-to-batch-counter[{0}]".format(idx),
                          "path": "counters/monasca.persister.pipeline.event.MetricHandler[metric-{0}].metrics-added-to-batch-counter/count".format(idx),
                          "type": "rate"
                          }
            whitelist.append(new_thread)

        config.merge(
            dropwizard_metrics(
                'monitoring',
                'monasca-persister',
                '{0}://localhost:{1}/metrics'.format(admin_endpoint_type,
                                                     admin_endpoint_port),
                whitelist))
        return config

    def dependencies_installed(self):
        return True


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
