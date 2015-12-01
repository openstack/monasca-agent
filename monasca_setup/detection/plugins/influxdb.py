import logging
import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)

# set up some defaults
whitelist = ['queriesRx', 'queriesExecuted', 'http_status', 'response_time']
metricmap = {'response_time': ['influxdb.response_time', 'gauge'],
             'http_status': ['influxdb.http_status', 'gauge'],
             'broadcastMessageTx': ['influxdb.broadcast_msg_tx', 'rate'],
             'writeSeriesMessageTx': ['influxdb.write_series_msg_tx', 'rate'],
             'queriesExecuted': ['influxdb.queries_executed', 'rate'],
             'queriesRx': ['influxdb.queries_rx', 'rate'],
             'shardsCreated': ['influxdb.shards_created', 'rate'],
             'broadcastMessageRx': ['influxdb.broadcast_msg_rx', 'rate'],
             'batchWriteRx': ['influxdb.batch_write_rx', 'rate'],
             'pointWriteRx': ['influxdb.point_write_rx', 'rate']}
params = {'q': 'SHOW STATS'}
dimensions = {'component': 'influxdb'}
timeout = 1
url = 'http://localhost:8086/query?'
collect_response_time = True

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
                            'metricmap': self.metricmap,
                            'collect_response_time':
                                self.collect_response_time,
                            'timeout': self.timeout,
                            'params': self.params,
                            'dimensions': self.dimensions}

                config['influxdb'] = {'init_config': None,
                                      'instances': [instance]}
            else:
                log.warn('Unable to access the InfluxDB diagnostics URL;' +
                         ' the InfluxDB plugin is not configured.' +
                         ' Please correct and re-run monasca-setup.')
        except Exception as e:
            log.exception('Error configuring the InfluxDB check plugin: {0} (error #{1})'.format(e.strerror, e.errno))
        return config

    def _connection_test(self):
        try:
            import httplib2
            from urllib import urlencode

            h = httplib2.Http(timeout=self.timeout)

            uri = self.url + urlencode(self.params)
            resp, content = h.request(uri, "GET")

            if 'content-type' in resp and 'application/json' in resp['content-type']:
                return True
        except Exception as e:
            log.error('Unable to access the InfluxDB diagnostics URL {0}: {1} (error #{2})'
                      .format(uri, e.strerror, e.errno))
        return False

    def _get_config(self):
        """Set the configuration to be used for connecting to InfluxDB
        :return:
        """

        # Set defaults and read config or use arguments
        self.url = url
        self.whitelist = whitelist
        self.metricmap = metricmap
        self.params = params
        self.dimensions = dimensions
        self.timeout = timeout
        self.collect_response_time = collect_response_time

        if self.args is not None:
            for arg in self.args:
                if arg == 'url':
                    self.url = self.args.get('url', url)
                else:
                    log.warn("Ignoring addition unsupported setup argument: {0}".format(arg))
