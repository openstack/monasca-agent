#!/bin/env python
"""Monitoring Agent plugin for InfluxDB HTTP/API checks.

"""

from httplib2 import Http
from httplib2 import httplib
from httplib2 import HttpLib2Error

<<<<<<< HEAD
=======
import json
>>>>>>> 8d9ebc5... An InfluxDB plugin to check status and performance metrics
import logging
import monasca_agent.collector.checks.services_checks as services_checks

import socket
import time
from urllib import urlencode

log = logging.getLogger(__name__)

GAUGE = "gauge"
RATE = "rate"


class InfluxDB(services_checks.ServicesCheck):

    def __init__(self, name, init_config, agent_config, instances=None):
        super(InfluxDB, self).__init__(name, init_config,
                                       agent_config, instances)

    @staticmethod
    def _load_conf(instance):
        # Fetches the conf
        url = instance.get('url', None)
        username = instance.get('username', None)
        password = instance.get('password', None)
        timeout = int(instance.get('timeout', 10))
        headers = instance.get('headers', {})
        whitelist = instance.get('whitelist', {})
        metricmap = instance.get('metricmap', {})
        params = instance.get('params', {'q': 'SHOW STATS'})
        uencode = instance.get('urlencode', True)
        response_time = instance.get('collect_response_time', False)

        if url is None:
            log.error("Bad configuration, no valid endpoint "
                      "(url) found in config!")
            raise Exception("Bad configuration. You must specify a url")
        ssl = instance.get('disable_ssl_validation', True)

        return url, username, password, timeout, headers, whitelist, \
            metricmap, params, uencode, response_time, ssl

    def _create_status_event(self, status, msg, instance):
        """Does nothing: status events are not yet supported by Mon API.

        """
        return

    def _check(self, instance):
        addr, username, password, timeout, headers, whitelist, metricmap, \
            params, encode, response_time, disable_ssl_validation, = \
            self._load_conf(instance)

        dimensions = self._set_dimensions({'url': addr}, instance)
        http_status_mname = 'http_status'
        http_status_mtype = GAUGE
        response_time_mname = 'response_time'
        response_time_mtype = GAUGE

        if http_status_mname in metricmap:
            http_status_mname, http_status_mtype = \
                tuple(metricmap[http_status_mname])
            # Otherwise you get a default

        if response_time_mname in metricmap:
            response_time_mname, response_time_mtype = \
                tuple(metricmap[response_time_mname])
            # Otherwise you get a default

        start = time.time()
        done = False
        retry = False
        while not done or retry:
            try:
                self.log.debug("Connecting to %s" % addr)
                if disable_ssl_validation:
                    self.warning(
                        "Skipping SSL certificate validation for %s based "
                        "on configuration" % addr)
                h = Http(timeout=timeout,
                         disable_ssl_certificate_validation=disable_ssl_validation)

                if username is not None and password is not None:
                    h.add_credentials(username, password)

                if params is not None:
                    if encode:
                        uri = addr + urlencode(params)
                    else:
                        uri = addr = params
                else:
                    uri = addr

                resp, content = h.request(uri, "GET", headers=headers)

            except (socket.timeout, HttpLib2Error, socket.error) as e:
                length = int((time.time() - start) * 1000)
                error_string = '{0} is DOWN, error: {1}. Connection failed ' \
                               'after {2} ms'.format(addr, str(e), length)
<<<<<<< HEAD
                self.log.info(error_string)
                if 'http_status' in whitelist:
                    if http_status_mtype == GAUGE:
                        self.gauge(http_status_mname,
                                   1,
                                   dimensions=dimensions,
                                   value_meta={'error': error_string})
                    elif http_status_mtype == RATE:
                        self.rate(http_status_mname,
                                  1,
                                  dimensions=dimensions,
                                  value_meta={'error': error_string})
=======
                self.push_error(error_string, dimensions, http_status_mname, http_status_mtype, whitelist)
>>>>>>> 8d9ebc5... An InfluxDB plugin to check status and performance metrics

                return services_checks.Status.DOWN, error_string

            except httplib.ResponseNotReady as e:
                length = int((time.time() - start) * 1000)
                error_string = '{0} is DOWN, error: {1}. Network is not ' \
                               'routable after {2} ms'.format(addr,
                                                              repr(e),
                                                              length)
<<<<<<< HEAD
                self.log.info(error_string)
                if 'http_status' in whitelist:
                    if http_status_mtype == GAUGE:
                            self.gauge(http_status_mname,
                                       1,
                                       dimensions=dimensions,
                                       value_meta={'error': error_string})
                    elif http_status_mtype == RATE:
                            self.rate(http_status_mname,
                                      1,
                                      dimensions=dimensions,
                                      value_meta={'error': error_string})
=======
                self.push_error(error_string, dimensions, http_status_mname, http_status_mtype, whitelist)
>>>>>>> 8d9ebc5... An InfluxDB plugin to check status and performance metrics

                return services_checks.Status.DOWN, error_string

            except Exception as e:
                length = int((time.time() - start) * 1000)
                error_string = '{0} is DOWN, error: {1}. Connection failed ' \
                               'after {2} ms'.format(addr, str(e), length)
                self.log.error('Unhandled exception {0}. Connection failed '
                               'after {1} ms'.format(str(e), length))

                if 'http_status' in whitelist:
                    if http_status_mtype == GAUGE:
                        self.gauge(http_status_mname,
                                   1,
                                   dimensions=dimensions,
                                   value_meta={'error': error_string})
                    elif http_status_mtype == RATE:
                        self.rate(http_status_mname,
                                  1,
                                  dimensions=dimensions,
                                  value_meta={'error': error_string})

                return services_checks.Status.DOWN, error_string

            if response_time:
                # Stop the timer as early as possible
                running_time = time.time() - start
                if 'response_time' in whitelist:
                    if response_time_mtype == GAUGE:
                        self.gauge(response_time_mname, running_time,
                                   dimensions=dimensions)
                    elif response_time_mtype == RATE:
                        self.rate(response_time_mname, running_time,
                                  dimensions=dimensions)

<<<<<<< HEAD
            if int(resp.status) >= 400:
                error_string = '{0} is DOWN, error code: {1}'\
                    .format(addr, str(resp.status))
                self.log.info(error_string)

                if 'http_status' in whitelist:
                    if http_status_mtype == GAUGE:
                        self.gauge(http_status_mname,
                                   1,
                                   dimensions=dimensions,
                                   value_meta={'error': error_string})
                    elif http_status_mtype == RATE:
                        self.rate(http_status_mname,
                                  1,
                                  dimensions=dimensions,
                                  value_meta={'error': error_string})
=======
            if int(resp.status) >= 500:
                error_string = '{0} is DOWN, error code: {1}'\
                    .format(addr, str(resp.status))
                self.push_error(error_string, dimensions, http_status_mname, http_status_mtype, whitelist)

                return services_checks.Status.DOWN, error_string
            elif int(resp.status) >= 400:
                error_string = 'InfluxDB check {0} causes HTTP errors when accessing {1}, error code: {2}'\
                    .format(instance.name, addr, str(resp.status))
                self.warning(error_string)
>>>>>>> 8d9ebc5... An InfluxDB plugin to check status and performance metrics

                return services_checks.Status.DOWN, error_string

            success_string = '{0} is UP'.format(addr)
            self.log.debug(success_string)

            if 'http_status' in whitelist:
                if http_status_mtype == GAUGE:
                    self.gauge(http_status_mname, 0, dimensions=dimensions)
                elif http_status_mtype == RATE:
                    self.rate(http_status_mname, 0, dimensions=dimensions)

            # If we got a JSON payload back from InfluxDB then we can push
            # metrics based on the data.
            if 'content-type' in resp and 'application/json' \
                    in resp['content-type']:
                self._rate_or_gauge_statuses(content,
                                             dimensions,
                                             whitelist,
                                             metricmap)

            done = True
            return services_checks.Status.UP, success_string

<<<<<<< HEAD
    def _rate_or_gauge_statuses(self, content, dimensions,
                                whitelist, metricmap):
        import json
=======
    def push_error(self, error_string, dimensions, http_status_mname, http_status_mtype, whitelist):
        self.log.info(error_string)
        if 'http_status' in whitelist:
            if http_status_mtype == GAUGE:
                self.gauge(http_status_mname,
                           1,
                           dimensions=dimensions,
                           value_meta={'error': error_string})
            elif http_status_mtype == RATE:
                self.rate(http_status_mname,
                          1,
                          dimensions=dimensions,
                          value_meta={'error': error_string})

    def _rate_or_gauge_statuses(self, content, dimensions,
                                whitelist, metricmap):
>>>>>>> 8d9ebc5... An InfluxDB plugin to check status and performance metrics
        statuses = {}
        measurements = {}

        data = json.loads(content)
        self.log.debug("data %s" % (data))
        if data and 'results' in data and 'series' in data['results'][0]:
            for d in data['results'][0]['series']:
<<<<<<< HEAD
                if 'name' in d:
                    name = d['name']
                    if 'server' in name:
                        columns = d['columns']
                        values = d['values'][0]

                        # Just make sure we have the same amount of
                        # data in both lists
                        if len(columns) == len(values):
                            cnt = 0
                            while cnt < len(columns):
                                cname = columns[cnt]
                                cval = values[cnt]
                                # See if we need to include the metric
                                if cname in whitelist:
                                    # See if we need to map it to the
                                    # preferred name
                                    if cname in metricmap:
                                        mname, mtype = tuple(metricmap[cname])
                                    # Otherwise just stuff in the original
                                    # name we got from InfluxDB and use
                                    # the default type of gauge
                                    else:
                                        mname, mtype = (cname, GAUGE)

                                    self.log.debug("values %s, cval %s, cnt %s, "
                                                   "mname %s, mtype %s, cname %s, "
                                                   "statuses %s"
                                                   % (values, cval, cnt, mname,
                                                      mtype, cname, statuses))

                                    statuses[cname] = (mname, mtype)
                                    measurements[mname] = cval
                                cnt += 1

        for status, metric in statuses.iteritems():
            metric_name, metric_type = metric
            value = float(measurements[metric_name])

            self.log.debug("status %s, statuses %s metric_name %s, "
                           "metric_type %s, measurements %s"
                           % (status, statuses, metric_name,
                              metric_type, measurements))

            if value is not None:
                if metric_type == RATE:
                    self.rate(metric_name, value, dimensions=dimensions)
                elif metric_type == GAUGE:
                    self.gauge(metric_name, value, dimensions=dimensions)
=======
                self.map_result(d, measurements, statuses, metricmap, whitelist)

            for status, metric in statuses.iteritems():
                metric_name, metric_type = metric
                value = measurements[metric_name]

                self.log.debug("status %s, statuses %s metric_name %s, "
                               "metric_type %s, measurements %s"
                               % (status, statuses, metric_name,
                                  metric_type, measurements))

                if value is not None:
                    if metric_type == RATE:
                        self.rate(metric_name, float(value), dimensions=dimensions)
                    elif metric_type == GAUGE:
                        self.gauge(metric_name, float(value), dimensions=dimensions)

    def map_result(self, stat_record, measurements, statuses, metricmap, whitelist):
        if 'name' in stat_record:
            name = stat_record['name']
            if 'server' in name:
                columns = stat_record['columns']
                values = stat_record['values'][0]

                # Just make sure we have the same amount of
                # data in both lists
                if len(columns) == len(values):
                    cnt = 0
                    while cnt < len(columns):
                        cname = columns[cnt]
                        cval = values[cnt]
                        # See if we need to include the metric
                        if cname in whitelist:
                            # See if we need to map it to the
                            # preferred name
                            if cname in metricmap:
                                mname, mtype = tuple(metricmap[cname])
                            # Otherwise just stuff in the original
                            # name we got from InfluxDB and use
                            # the default type of gauge
                            else:
                                mname, mtype = (cname, GAUGE)

                            self.log.debug("values %s, cval %s, cnt %s, "
                                           "mname %s, mtype %s, cname %s, "
                                           "statuses %s"
                                           % (values, cval, cnt, mname,
                                              mtype, cname, statuses))

                            statuses[cname] = (mname, mtype)
                            measurements[mname] = cval
                        cnt += 1
>>>>>>> 8d9ebc5... An InfluxDB plugin to check status and performance metrics
