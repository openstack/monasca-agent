"""Classes for monitoring the monitoring server stack.

    Covering mon-persister, mon-api and mon-thresh.
    Kafka, mysql, vertica and influxdb are covered by other detection plugins. Mon-notification uses statsd.
"""

import logging

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)


class MonPersister(monasca_setup.detection.Plugin):
    """Detect mon_persister and setup monitoring.
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """
        if monasca_setup.detection.find_process_cmdline('mon-persister') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        log.info("\tEnabling the mon persister healthcheck")
        return dropwizard_health_check('mon-persister', 'http://localhost:8091/healthcheck')

        # todo
        # log.info("\tEnabling the mon persister metric collection")
        # http://localhost:8091/metrics

    def dependencies_installed(self):
        return True


class MonAPI(monasca_setup.detection.Plugin):
    """Detect mon_api and setup monitoring.
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        monasca_api = monasca_setup.detection.find_process_cmdline('monasca-api')
        if monasca_api is not None:
            # monasca-api can show up in urls and be an arg to this setup program, check port also
            for conn in monasca_api.connections('inet'):
                if conn.laddr[1] == 8080:
                    self.available = True
                    return

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        log.info("\tEnabling the mon api healthcheck")
        return dropwizard_health_check('mon-api', 'http://localhost:8081/healthcheck')

        # todo
        # log.info("\tEnabling the mon api metric collection")
        # http://localhost:8081/metrics

    def dependencies_installed(self):
        return True


class MonThresh(monasca_setup.detection.Plugin):

    """Detect the running mon-thresh and monitor.

    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        if monasca_setup.detection.find_process_cmdline('mon-thresh') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        log.info("\tWatching the mon-thresh process.")
        return monasca_setup.detection.watch_process(['mon-thresh'])

    def dependencies_installed(self):
        return True


def dropwizard_health_check(name, url):
    """Setup a dropwizard heathcheck to be watched by the http_check plugin.

    """
    config = monasca_setup.agent_config.Plugins()
    config['http_check'] = {'init_config': None,
                            'instances': [{'name': name,
                                           'url': url,
                                           'timeout': 1,
                                           'include_content': False}]}
    return config
