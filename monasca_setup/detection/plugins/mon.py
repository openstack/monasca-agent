"""Classes for monitoring the monitoring server stack.

    Covering mon-persister, mon-api and mon-thresh.
    Kafka, mysql, vertica and influxdb are covered by other detection plugins. Mon-notification uses statsd.
"""

import logging
import yaml

import monasca_setup.agent_config
import monasca_setup.detection
from monasca_setup.detection import find_process_cmdline, watch_process

log = logging.getLogger(__name__)


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
                    self.api_config = yaml.load(config.read())
            except Exception:
                log.exception('Failed parsing /etc/monasca/api-config.yml')
                self.available = False
                return
            api_port = self.api_config['server']['applicationConnectors'][0]['port']
            for conn in monasca_api.connections('inet'):
                if conn.laddr[1] == api_port:
                    self.available = True
                    return

    def build_config(self):
        """Build the config as a Plugins object and return."""
        log.info("\tEnabling the Monasca api healthcheck")
        admin_port = self.api_config['server']['adminConnectors'][0]['port']
        config = monasca_setup.agent_config.Plugins()
        config.merge(dropwizard_health_check('monitoring', 'api', 'http://localhost:8081/healthcheck'))

        log.info("\tEnabling the Monasca api metrics")
        whitelist = [
            {
                "name": "jvm.memory.total.max",
                "path": "gauges/jvm.memory.total.max/value",
                "type": "gauge"},
            {
                "name": "jvm.memory.total.used",
                "path": "gauges/jvm.memory.total.used/value",
                "type": "gauge"},
            {
                "name": "metrics.published",
                "path": "meters/monasca.api.app.MetricService.metrics.published/count",
                "type": "rate"},
            {
                "name": "raw-sql.time.avg",
                "path": "timers/org.skife.jdbi.v2.DBI.raw-sql/mean",
                "type": "gauge"},
            {
                "name": "raw-sql.time.max",
                "path": "timers/org.skife.jdbi.v2.DBI.raw-sql/max",
                "type": "gauge"},
        ]
        config.merge(dropwizard_metrics('monitoring', 'api', 'http://localhost:8081/metrics', whitelist))
        return config

    def dependencies_installed(self):
        return True


class MonNotification(monasca_setup.detection.Plugin):
    """Detect the Monsaca notification engine and setup some simple checks."""
    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        if find_process_cmdline('monasca-notification') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return."""
        log.info("\tEnabling the Monasca Notification healthcheck")
        return watch_process(['monasca-notification'], 'monitoring', 'notification', exact_match=False)

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
        log.info("\tEnabling the Monasca persister healthcheck")
        config = monasca_setup.agent_config.Plugins()
        config.merge(dropwizard_health_check('monitoring', 'persister', 'http://localhost:8091/healthcheck'))

        log.info("\tEnabling the Monasca persister metrics")
        whitelist = [
            {
                "name": "jvm.memory.total.max",
                "path": "gauges/jvm.memory.total.max/value",
                "type": "gauge"},
            {
                "name": "jvm.memory.total.used",
                "path": "gauges/jvm.memory.total.used/value",
                "type": "gauge"},
            {
                "name": "alarm-state-transitions-added-to-batch-counter[0]",
                "path": "counters/monasca.persister.pipeline.event.AlarmStateTransitionHandler[alarm-state-transition-0].alarm-state-transitions-added-to-batch-counter/count",
                "type": "rate"},
            {
                "name": "alarm-state-transitions-added-to-batch-counter[1]",
                "path": "counters/monasca.persister.pipeline.event.AlarmStateTransitionHandler[alarm-state-transition-1].alarm-state-transitions-added-to-batch-counter/count",
                "type": "rate"},
            {
                "name": "metrics-added-to-batch-counter[0]",
                "path": "counters/monasca.persister.pipeline.event.MetricHandler[metric-0].metrics-added-to-batch-counter/count",
                "type": "rate"},
            {
                "name": "metrics-added-to-batch-counter[1]",
                "path": "counters/monasca.persister.pipeline.event.MetricHandler[metric-1].metrics-added-to-batch-counter/count",
                "type": "rate"},
            {
                "name": "metrics-added-to-batch-counter[2]",
                "path": "counters/monasca.persister.pipeline.event.MetricHandler[metric-2].metrics-added-to-batch-counter/count",
                "type": "rate"},
            {
                "name": "metrics-added-to-batch-counter[3]",
                "path": "counters/monasca.persister.pipeline.event.MetricHandler[metric-3].metrics-added-to-batch-counter/count",
                "type": "rate"}
        ]
        config.merge(dropwizard_metrics('monitoring', 'persister', 'http://localhost:8091/metrics', whitelist))
        return config

    def dependencies_installed(self):
        return True


class MonThresh(monasca_setup.detection.Plugin):
    """Detect the running mon-thresh and monitor."""
    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        if find_process_cmdline('backtype.storm.daemon') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return."""
        log.info("\tWatching the mon-thresh process.")
        config = monasca_setup.agent_config.Plugins()
        for process in ['backtype.storm.daemon.nimbus', 'backtype.storm.daemon.supervisor', 'backtype.storm.daemon.worker']:
            if find_process_cmdline(process) is not None:
                config.merge(watch_process([process], 'monitoring', 'storm', exact_match=False))
        return config

    def dependencies_installed(self):
        return True


def dropwizard_health_check(service, component, url):
    """Setup a dropwizard heathcheck to be watched by the http_check plugin."""
    config = monasca_setup.agent_config.Plugins()
    config['http_check'] = {'init_config': None,
                            'instances': [{'name': "{0}-{1} healthcheck".format(service, component),
                                           'url': url,
                                           'timeout': 1,
                                           'include_content': False,
                                           'dimensions': {'service': service, 'component': component}}]}
    return config


def dropwizard_metrics(service, component, url, whitelist):
    """Setup a dropwizard metrics check"""
    config = monasca_setup.agent_config.Plugins()
    config['http_metrics'] = {'init_config': None,
                              'instances': [{'name': "{0}-{1} metrics".format(service, component),
                                             'url': url,
                                             'timeout': 1,
                                             'dimensions': {'service': service, 'component': component},
                                             'whitelist': whitelist}]}
    return config
