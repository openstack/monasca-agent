#!/bin/env python
"""Monitoring Agent plugin for InfluxDB HTTP/API checks.

"""

import monasca_agent.collector.checks.services_checks as services_checks
import monasca_agent.common.util as util

import requests

GAUGE = 'gauge'
RATE = 'rate'
TYPE_KEY = 'type'
INFLUXDB_NAME_KEY = 'influxdb_name'
DIMENSIONS_KEY = '_dimensions'

HTTP_STATUS_MNAME = "http_status"

# meaningful defaults, keep configuration small (currently only for 0.9.4)
DEFAULT_METRICS_WHITELIST = {'httpd': ['auth_fail', 'points_write_ok', 'query_req', 'write_req'],
                             'engine': ['points_write', 'points_write_dedupe'],
                             'shard': ['series_create', 'fields_create', 'write_req', 'points_write_ok']}

# ['queriesRx', 'queriesExecuted', 'http_status', 'response_time']
DEFAULT_METRICS_DEF = {
    'httpd': {
        DIMENSIONS_KEY: {'binding': 'bind'},
        'auth_fail': {TYPE_KEY: RATE},
        'points_write_ok': {TYPE_KEY: RATE, INFLUXDB_NAME_KEY: 'points_written_ok'},
        'query_req': {TYPE_KEY: RATE},
        'query_resp_bytes': {TYPE_KEY: RATE},
        'req': {TYPE_KEY: RATE},
        'write_req': {TYPE_KEY: RATE},
        'write_req_bytes': {TYPE_KEY: RATE}},
    'engine': {
        DIMENSIONS_KEY: {'path': 'path'},
        'blks_write': {TYPE_KEY: RATE},
        'blks_write_bytes': {TYPE_KEY: RATE},
        'blks_write_bytes_c': {TYPE_KEY: RATE},
        'points_write': {TYPE_KEY: RATE},
        'points_write_dedupe': {TYPE_KEY: RATE}},
    'shard': {
        DIMENSIONS_KEY: {'influxdb_engine': 'engine', 'influxdb_shard': 'id'},
        'fields_create': {TYPE_KEY: RATE},
        'series_create': {TYPE_KEY: RATE},
        'write_points_ok': {TYPE_KEY: RATE},
        'write_req': {TYPE_KEY: RATE}},
    'wal': {
        DIMENSIONS_KEY: {'path': 'path'},
        'auto_flush': {TYPE_KEY: RATE},
        'flush_duration': {TYPE_KEY: RATE},
        'idle_flush': {TYPE_KEY: RATE},
        'mem_size': {TYPE_KEY: RATE},
        'meta_flush': {TYPE_KEY: RATE},
        'points_flush': {TYPE_KEY: RATE},
        'points_write': {TYPE_KEY: RATE},
        'points_write_req': {TYPE_KEY: RATE},
        'series_flush': {TYPE_KEY: RATE}},
    'write': {
        DIMENSIONS_KEY: {'path': 'path'},
        'point_req': {TYPE_KEY: RATE},
        'point_req_local': {TYPE_KEY: RATE},
        'req': {TYPE_KEY: RATE},
        'write_ok': {TYPE_KEY: RATE}},
    'runtime': {
        'alloc': {TYPE_KEY: RATE, INFLUXDB_NAME_KEY: 'Alloc'},
        'frees': {TYPE_KEY: RATE, INFLUXDB_NAME_KEY: 'Frees'},
        'heap_alloc': {TYPE_KEY: RATE, INFLUXDB_NAME_KEY: 'HeapAlloc'},
        'heap_idle': {TYPE_KEY: RATE, INFLUXDB_NAME_KEY: 'HeapIdle'},
        'heap_in_use': {TYPE_KEY: RATE, INFLUXDB_NAME_KEY: 'HeapInUse'},
        'heap_objects': {TYPE_KEY: RATE, INFLUXDB_NAME_KEY: 'HeapObjects'},
        'heap_released': {TYPE_KEY: RATE, INFLUXDB_NAME_KEY: 'HeapReleased'},
        'heap_sys': {TYPE_KEY: RATE, INFLUXDB_NAME_KEY: 'HeapSys'},
        'lookups': {TYPE_KEY: RATE, INFLUXDB_NAME_KEY: 'Lookups'},
        'mallocs': {TYPE_KEY: RATE, INFLUXDB_NAME_KEY: 'Mallocs'},
        'num_gc': {TYPE_KEY: RATE, INFLUXDB_NAME_KEY: 'NumGC'},
        'num_goroutine': {TYPE_KEY: RATE, INFLUXDB_NAME_KEY: 'NumGoroutine'},
        'pause_total_ns': {TYPE_KEY: RATE, INFLUXDB_NAME_KEY: 'PauseTotalNs'},
        'sys': {TYPE_KEY: GAUGE, INFLUXDB_NAME_KEY: 'Sys'},
        'total_alloc': {TYPE_KEY: GAUGE, INFLUXDB_NAME_KEY: 'TotalAlloc'}}}
DEFAULT_QUERY = 'SHOW STATS'
DEFAULT_URL = 'localhost:8086'
PARAMS = {'q': DEFAULT_QUERY}


class InfluxDB(services_checks.ServicesCheck):
    def __init__(self, name, init_config, agent_config, instances=None):
        super(InfluxDB, self).__init__(name, init_config,
                                       agent_config, instances)

    def _load_conf(self, instance):
        # Fetches the conf
        base_url = instance.get('url', DEFAULT_URL).rstrip('/')
        username = instance.get('username', None)
        password = instance.get('password', None)
        timeout = float(instance.get('timeout', '1'))
        headers = instance.get('headers', {})
        whitelist = instance.get('whitelist', DEFAULT_METRICS_WHITELIST)
        metricdef = instance.get('metricdef', DEFAULT_METRICS_DEF)
        collect_response_time = instance.get('collect_response_time', False)
        disable_ssl_validation = instance.get('disable_ssl_validation', True)

        if disable_ssl_validation:
            self.log.info('Skipping SSL certificate validation for %s based '
                          'on configuration', base_url)

        endpoint = base_url + '/query'

        return endpoint, username, password, timeout, headers, whitelist, metricdef, \
            collect_response_time, disable_ssl_validation

    def _create_status_event(self, status, msg, instance):
        """Does nothing: status events are not yet supported by Mon API.

        """
        return

    def _push_error(self, error_string, dimensions):
        self.log.error(error_string)
        self.warning(error_string)
        self.gauge(HTTP_STATUS_MNAME, 1, dimensions=dimensions, value_meta={'error': error_string})

    def _rate_or_gauge_statuses(self, content, dimensions, whitelist, metricdef):

        trans = {}  # tabular content transformed into real dictionary
        self.log.debug('data: %s', content)
        # create complete map
        for results in content['results']:
            for ser in results['series']:
                mod = ser['name']
                if mod in whitelist:  # pre-filter by module
                    trans[mod] = {}
                    for i, col in enumerate(ser['columns']):
                        trans[mod][col] = ser['values'][0][i]
                    trans[mod][DIMENSIONS_KEY] = ser['tags']

        # extract required metrics per whitelisted module
        for mod, met_list in metricdef.iteritems():
            if mod not in whitelist:
                continue
            dims = dimensions.copy()
            for met, met_def in met_list.iteritems():
                if met == DIMENSIONS_KEY:  # map tags to appropriate dimensions
                    for k, v in met_def.iteritems():
                        dims[k] = trans[mod][DIMENSIONS_KEY][v]
                else:
                    met_type = met_def[TYPE_KEY]
                    met_iname = met_def.get(INFLUXDB_NAME_KEY, met)
                    fqmet = 'influxdb.{0}.{1}'.format(mod, met)
                    if met_iname in trans[mod]:
                        value = trans[mod][met_iname]
                        self._push_metric(met_type, fqmet, value, dims)
                    else:
                        self.log.debug('InfluxDB did not report metric %s.%s', mod, met_iname)

    def _push_metric(self, metric_type, metric_name, metric_value, dimensions):
        self.log.debug('push %s %s = %s {%s}', metric_type, metric_name, dimensions)

        if metric_type == RATE:
            self.rate(metric_name, float(metric_value), dimensions=dimensions)
        elif metric_type == GAUGE:
            self.gauge(metric_name, float(metric_value), dimensions=dimensions)

    def _check(self, instance):
        endpoint, username, password, timeout, headers, whitelist, metricdef, \
            collect_response_time, disable_ssl_validation = self._load_conf(instance)

        timer = util.Timer()
        merged_dimensions = self._set_dimensions({'component': 'influxdb', 'url': endpoint}, instance)

        try:
            merged_headers = headers.copy()
            merged_headers.update(util.headers(self.agent_config))
            if username is not None and password is not None:
                auth = (username, password)
            else:
                auth = None
            self.log.debug('Query InfluxDB using GET to %s', endpoint)
            resp = requests.get(endpoint, params=PARAMS, headers=merged_headers, auth=auth, timeout=self.timeout,
                                verify=not disable_ssl_validation)
            content = resp.json()

            # report response time first, even when there is HTTP errors
            if collect_response_time:
                # Stop the timer as early as possible
                running_time = timer.total()
                self.gauge('http_response_time', running_time, dimensions=merged_dimensions)

            # check HTTP errors
            if int(resp.status_code) >= 500:
                error_string = '{0} is DOWN, error code: {1}'.format(endpoint, resp.status_code)
                self._push_error(error_string, merged_dimensions)
                return services_checks.Status.DOWN, error_string

            elif int(resp.status_code) >= 400:
                error_string = "InfluxDB check {0} causes HTTP errors when accessing {1}, error code: {2}".format(
                        instance.get('name'), endpoint, resp.status_code)
                self.warning(error_string)
                return services_checks.Status.DOWN, error_string

            # check content
            if 'application/json' not in resp.headers.get('content-type', []):
                error_string = "InfluxDB check {0} received unexpected payload when accessing {1}: content_type={2}" \
                    .format(
                        instance['name'], endpoint, resp.headers['content-type'])
                self.warning(error_string)
                return services_checks.Status.DOWN, error_string

            self._rate_or_gauge_statuses(content, merged_dimensions, whitelist, metricdef)
            success_string = '{0} is UP'.format(endpoint)
            self.log.debug(success_string)
            self.gauge(HTTP_STATUS_MNAME, 0, dimensions=merged_dimensions)
            return services_checks.Status.UP, success_string

        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
            error_string = '{0} is not reachable via network, error: {1}'.format(endpoint, repr(e))
            self._push_error(error_string, merged_dimensions)
            return services_checks.Status.DOWN, error_string

        except requests.exceptions.Timeout as e:
            length = timer.total()*1000.0
            error_string = '{0} did not respond within {2} ms, error: {1}.'.format(endpoint,
                                                                                   repr(e),
                                                                                   length)
            self._push_error(error_string, merged_dimensions)
            return services_checks.Status.DOWN, error_string

        except requests.exceptions.RequestException as e:
            error_string = 'Unhandled exception {0}'.format(repr(e))
            self.log.exception(error_string)
            self.warning(error_string)
            return services_checks.Status.DOWN, error_string

        except (KeyError, TypeError) as e:
            error_string = "Unsupported schema returned by query endpoint of instance {0}: {1}".format(
                    instance.get('url'), repr(e))
            self.log.exception(error_string)
            return services_checks.Status.UP, error_string
