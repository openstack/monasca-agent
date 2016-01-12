import logging
import monasca_agent.collector.checks_d.influxdb as influxdb
import monasca_setup.agent_config
import monasca_setup.detection as detection
import requests

log = logging.getLogger(__name__)

# set up some defaults
DEFAULT_TIMEOUT = 1
DEFAULT_COLLECT_RESPONSE_TIME = True


class InfluxDB(monasca_setup.detection.ArgsPlugin):
    """Setup an InfluxDB according to the passed in args.
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """

        self.influxd = detection.find_process_name('influxd')
        if self.influxd is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()

        try:
            # do not add another instance if there is already something configured
            if self._get_config():
                log.info("\tEnabling the InfluxDB check for {:s}".format(self.url))
                instance = {'name': 'localhost',
                            'url': self.url,
                            'username': self.username,
                            'password': self.password,
                            'whitelist': self.whitelist,
                            'collect_response_time':
                                self.collect_response_time,
                            }
                if self.timeout is not None:
                    instance['timeout'] = self.timeout
                # extract stats continuously
                config['influxdb'] = {'init_config': None,
                                      'instances': [instance]}
                # watch processes using process plugin
                config.merge(detection.watch_process(['influxd'], component='influxdb', exact_match=False))
            else:
                log.warn('Unable to access the InfluxDB diagnostics URL;' +
                         ' the InfluxDB plugin is not configured.' +
                         ' Please correct and re-run monasca-setup.')
        except Exception as e:
            log.exception('Error configuring the InfluxDB check plugin: %s', repr(e))

        return config

    def _connection_test(self, url):
        try:
            log.debug('Attempting to connect to InfluxDB API at %s', self.url)
            uri = url + "/ping"
            resp = requests.get(url=uri, timeout=self.timeout)
            self.version = resp.headers.get('x-influxdb-version', '0 (unknown)')
            log.info('Discovered InfluxDB version %s', self.version)

            # this will work for 0.9.4 but not necessarily future stable releases (e.g. 1.0.11)
            supported = self.version >= '0.9.4'
            if not supported:
                log.error('Unsupported InfluxDB version: {0}'.format(self.version))
            return supported

        except Exception as e:
            log.exception('Unable to access the InfluxDB query URL %s: %s', self.url, repr(e))

        return False

    def _discover_config(self):
        # discover API port
        for conn in self.influxd.connections('inet'):
            for protocol in ['http', 'https']:
                u = '{0}://localhost:{1}'.format(protocol, conn.laddr[0])
                if self._connection_test(u):
                    self.url = u
                    return True
        return False

    def _get_config(self):
        """Set the configuration to be used for connecting to InfluxDB
        """

        # Set defaults and read config or use arguments
        self.url = influxdb.DEFAULT_URL
        self.whitelist = influxdb.DEFAULT_METRICS_WHITELIST
        self.timeout = DEFAULT_TIMEOUT
        self.collect_response_time = DEFAULT_COLLECT_RESPONSE_TIME

        # when args have been passed, then not self discovery is attempted
        if self.args is not None:
            self.username = self.args.get('influxdb.username', None)
            self.password = self.args.get('influxdb.password', None)
            self.timeout = self.args.get('influxdb.timeout', None)
            self.collect_response_time = self.args.get('collect_response_time', DEFAULT_COLLECT_RESPONSE_TIME)
            return self._connection_test(self.url) or self._discover_config()
        else:
            log.warning("No username and password supplied to InfluxDB detection!")
            return self._discover_config()
