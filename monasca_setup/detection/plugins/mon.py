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
        return dropwizard_health_check('monitoring', 'api', 'http://localhost:{0}/healthcheck'.format(admin_port))

        # todo
        # log.info("\tEnabling the mon api metric collection")
        # http://localhost:8081/metrics

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
        return dropwizard_health_check('monitoring', 'persister', 'http://localhost:8091/healthcheck')

        # todo
        # log.info("\tEnabling the mon persister metric collection")
        # http://localhost:8091/metrics

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
