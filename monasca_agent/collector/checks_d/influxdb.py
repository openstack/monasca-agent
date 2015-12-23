#!/bin/env python
"""Monitoring Agent plugin for InfluxDB HTTP/API checks.

"""

import json
import socket
import time
from urllib import urlencode

from httplib2 import Http
from httplib2 import HttpLib2Error
from httplib2 import httplib

import monasca_agent.collector.checks.services_checks as services_checks
import monasca_agent.common.util as util

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
DEFAULT_METRICS_DEF = {'httpd': {
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
DEFAULT_DIMENSIONS = {'component': 'influxdb'}
DEFAULT_QUERY = 'SHOW STATS'


class InfluxDB(services_checks.ServicesCheck):
    def __init__(self, name, init_config, agent_config, instances=None):
        super(InfluxDB, self).__init__(name, init_config,
                                       agent_config, instances)

    def _load_conf(self, instance):
        # Fetches the conf
        base_url = instance.get('url', None)
        query = instance.get('query', DEFAULT_QUERY)
        username = instance.get('username', None)
        password = instance.get('password', None)
        timeout = int(instance.get('timeout', 10))
        headers = instance.get('headers', {})
        whitelist = instance.get('whitelist', DEFAULT_METRICS_WHITELIST)
        metricdef = instance.get('metricdef', DEFAULT_METRICS_DEF)
        dimensions = instance.get('dimensions', {})
        collect_response_time = instance.get('collect_response_time', False)
        disable_ssl_validation = instance.get('disable_ssl_validation', True)

        if disable_ssl_validation:
            self.log.info('Skipping SSL certificate validation for %s based '
                          'on configuration', base_url)
        if base_url is None:
            self.log.error("Bad configuration, no valid base URL "
                           "(url) found in config!")
            raise Exception("Bad configuration. You must specify a url")

        endpoint = base_url + '/query'

        return endpoint, query, username, password, timeout, headers, dimensions, whitelist, metricdef, \
                    collect_response_time, disable_ssl_validation

    def _create_status_event(self, status, msg, instance):
        """Does nothing: status events are not yet supported by Mon API.

        """
        return

    def _push_error(self, error_string, dimensions):
        self.warning(error_string)
        self.gauge(HTTP_STATUS_MNAME, 1, dimensions=dimensions, value_meta={'error': error_string})

    def _rate_or_gauge_statuses(self, content, dimensions, whitelist, metricdef):

        trans = {}  # tabular content transformed into real dictionary
        data = json.loads(content)
        self.log.debug('data: %s', data)
        # create complete map
        for results in data['results']:
            for ser in results['series']:
                mod = ser['name']
                if mod in whitelist:  # pre-filter by module
                    trans[mod] = {}
                    i = 0
                    for col in ser['columns']:
                        trans[mod][col] = ser['values'][i]
                        i += 1
                    trans[mod][DIMENSIONS_KEY] = ser['tags']

        # extract required metrics per whitelisted module
        for mod, met_list in metricdef:
            dims = dimensions.copy()
            for met, met_def in met_list:
                if met == DIMENSIONS_KEY:  # map tags to appropriate dimensions
                    for k, v in met_def:
                        dims[k] = trans[mod][DIMENSIONS_KEY][v]
                else:
                    met_type = met_def[TYPE_KEY]
                    met_iname = met_def.get(INFLUXDB_NAME_KEY, met)
                    if met_iname in trans[mod]:
                        value = trans[mod][met_iname]
                        self._push_metric(met_type, met, value, dims)
                    else:
                        self.log.warn('InfluxDB does not report metric %s.%s', mod, met_iname)

    def _push_metric(self, metric_type, metric_name, metric_value, dimensions):
        self.log.debug('push %s %s = %s {%s}', metric_type, metric_name, dimensions)

        if metric_type == RATE:
            self.rate(metric_name, float(metric_value), dimensions=dimensions)
        elif metric_type == GAUGE:
            self.gauge(metric_name, float(metric_value), dimensions=dimensions)

    def _check(self, instance):
        endpoint, query, username, password, timeout, headers, dimensions, whitelist, metricdef, \
                collect_response_time, disable_ssl_validation = self._load_conf(instance)

        start_time = time.time()
        content = ""
        merged_dimensions = self._set_dimensions(
                {'component': 'influxdb', 'url': endpoint}.update(dimensions.copy()), instance)

        try:
            h = Http(timeout=timeout, disable_ssl_certificate_validation=disable_ssl_validation)
            if username is not None and password is not None:
                h.add_credentials(username, password)

            params = {'q': query}
            merged_headers = headers.copy()
            merged_headers.update(util.headers(self.agent_config))

            uri = '{0}?{1}'.format(endpoint, urlencode(params))

            self.log.debug('Query InfluxDB using GET to %s', uri)
            resp, content = h.request(uri, "GET", headers=merged_headers)

            # report response time first, even when there is HTTP errors
            if collect_response_time:
                # Stop the timer as early as possible
                running_time = time.time() - start_time
                self.gauge('http_response_time', running_time, dimensions=merged_dimensions)

            # check HTTP errors
            if int(resp.status) >= 500:
                error_string = '{0} is DOWN, error code: {1}'.format(endpoint, str(resp.status))
                self._push_error(error_string, merged_dimensions)
                return services_checks.Status.DOWN, error_string

            elif int(resp.status) >= 400:
                error_string = "InfluxDB check {0} causes HTTP errors when accessing {1}, error code: {2}".format(
                        instance.get('name'), uri, str(resp.status))
                self.warning(error_string)
                return services_checks.Status.DOWN, error_string

            # check content
            if 'application/json' not in resp.get('content-type', []):
                error_string = "InfluxDB check {0} received unexpected payload when accessing {1}: content_type={2}" \
                    .format(
                        instance['name'], uri, str(resp['content-type']))
                self.warning(error_string)
                return services_checks.Status.DOWN, error_string

            self._rate_or_gauge_statuses(content, merged_dimensions, whitelist, metricdef)
            success_string = '{0} is UP'.format(endpoint)
            self.log.debug(success_string)
            self.gauge(HTTP_STATUS_MNAME, 0, dimensions=merged_dimensions)
            return services_checks.Status.UP, success_string

        except (socket.timeout, HttpLib2Error, socket.error) as e:
            length = int((time.time() - start_time) * 1000)
            error_string = '{0} is DOWN, error: {1}. Connection failed ' \
                           'after {2} ms'.format(endpoint, str(e), length)
            self._push_error(error_string, merged_dimensions)
            return services_checks.Status.DOWN, error_string

        except httplib.ResponseNotReady as e:
            length = int((time.time() - start_time) * 1000)
            error_string = '{0} is DOWN, error: {1}. Network is not ' \
                           'routable after {2} ms'.format(endpoint,
                                                          repr(e),
                                                          length)
            self._push_error(error_string, merged_dimensions)
            return services_checks.Status.DOWN, error_string

        except (KeyError, TypeError) as e:
            error_string = "Unsupported schema returned by query endpoint of instance {0}: {1}".format(
                    instance.get('url'), str(e))
            self.log.exception(error_string)
            self.log.debug('received: %s', content)
            return services_checks.Status.UP, error_string

        except Exception as e:
            length = int((time.time() - start_time) * 1000)
            error_string = 'Unhandled exception {0}. Connection failed after {1} ms'.format(str(e), length)
            self.log.exception(error_string)
            self.warning(error_string)
            return services_checks.Status.DOWN, error_string
