import httplib2
import logging
import monasca_agent.collector.checks_d.influxdb as influxdb
import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)

# set up some defaults
DEFAULT_TIMEOUT = 1
DEFAULT_RENAME = 'http://localhost:8086'
DEFAULT_COLLECT_RESPONSE_TIME = True


class InfluxDB(monasca_setup.detection.ArgsPlugin):
    """Setup an InfluxDB according to the passed in args.
       Despite being a detection plugin this plugin does no detection
       and will be a noop without arguments.
       Expects space separated arguments, the required argument is url.
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """

        if monasca_setup.detection.find_process_name('influxd') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()

        try:
            self._get_config()
            log.info("\tEnabling the InfluxDB check for {:s}".format(self.url))

            if self._connection_test():
                instance = {'name': self.url,
                            'url': self.url,
                            'whitelist': self.whitelist,
                            'collect_response_time':
                                self.collect_response_time,
                            'timeout': self.timeout}

                config['influxdb'] = {'init_config': None,
                                      'instances': [instance]}
            else:
                log.warn('Unable to access the InfluxDB diagnostics URL;' +
                         ' the InfluxDB plugin is not configured.' +
                         ' Please correct and re-run monasca-setup.')
        except Exception as e:
            log.exception('Error configuring the InfluxDB check plugin: %s', str(e))

        return config

    def _connection_test(self):
        try:
            log.info('Attempting to connect to InfluxDB at %s', self.url)
            h = httplib2.Http(timeout=self.timeout)

            uri = self.url + "/ping"
            resp, content = h.request(uri, "GET")
            self.version = resp.get('x-influxdb-version', '0')
            log.debug('')
            log.info('Discovered InfluxDB version %s', self.version)

            return self.version >= '0.9.4'

        except Exception as e:
            log.error('Unable to access the InfluxDB query URL %s: %s', self.url, str(e))

        return False

    def _get_config(self):
        """Set the configuration to be used for connecting to InfluxDB
        :return:
        """

        # Set defaults and read config or use arguments
        self.url = DEFAULT_RENAME
        self.whitelist = influxdb.DEFAULT_METRICS_WHITELIST
        self.timeout = DEFAULT_TIMEOUT
        self.collect_response_time = DEFAULT_COLLECT_RESPONSE_TIME

        if self.args is not None:
            for key, val in self.args:
                if key == 'url':
                    self.url = val
                elif key == 'timeout':
                    self.timeout = val
                elif key == 'collect_response_time':
                    self.collect_response_time = val
                else:
                    log.warn("Ignoring addition unsupported setup argument: {0}".format(key))
