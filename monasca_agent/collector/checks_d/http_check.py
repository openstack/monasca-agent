#!/bin/env python
# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP
"""Monitoring Agent plugin for HTTP/API checks.

"""

import os
import re
import socket
import sys
import time

from httplib2 import Http
from httplib2 import httplib
from httplib2 import HttpLib2Error

import monasca_agent.collector.checks.services_checks as services_checks
import monasca_agent.common.config as cfg
import monasca_agent.common.keystone as keystone


class HTTPCheck(services_checks.ServicesCheck):

    def __init__(self, name, init_config, agent_config, instances=None):
        super(HTTPCheck, self).__init__(name, init_config, agent_config,
                                        instances)
        # init the keystone client if instance has use_keystone
        self._api_config = cfg.Config().get_config('Api')
        self._ksclients = {}
        for instance in instances:
            addr, username, password, timeout, headers, response_time, \
                disable_ssl_validation, use_keystone, keystone_config, \
                instance_name = self._load_http_conf(instance)
            if use_keystone:
                # keystone is a singleton. It will be initialized once,
                # the first config instance used.
                if keystone_config:
                    ksclient = keystone.Keystone(keystone_config)
                else:
                    ksclient = keystone.Keystone(self._api_config)
                self._ksclients[instance_name] = ksclient

    @staticmethod
    def _load_http_conf(instance):
        # Fetches the conf
        instance_name = instance.get('name', None)
        if instance_name is None:
            raise Exception("Bad configuration. You must specify a name")
        username = instance.get('username', None)
        password = instance.get('password', None)
        timeout = int(instance.get('timeout', 10))
        headers = instance.get('headers', {})
        headers.setdefault('User-Agent', os.path.basename(sys.argv[0]))
        use_keystone = instance.get('use_keystone', False)
        keystone_config = instance.get('keystone_config', None)
        url = instance.get('url', None)
        response_time = instance.get('collect_response_time', False)
        if url is None:
            raise Exception("Bad configuration. You must specify a url")
        ssl = instance.get('disable_ssl_validation', True)

        return url, username, password, timeout, headers, response_time, \
            ssl, use_keystone, keystone_config, instance_name

    def _create_status_event(self, status, msg, instance):
        """Does nothing: status events are not yet supported by Mon API.
        """
        return

    def _http_check(self, instance):
        addr, username, password, timeout, headers, response_time, \
            disable_ssl_validation, use_keystone, keystone_config, \
            instance_name = self._load_http_conf(instance)
        dimensions = self._set_dimensions({'url': addr}, instance)

        start = time.time()

        done = False
        retry = False
        while not done or retry:
            if use_keystone:
                ksclient = self._ksclients[instance_name]
                token = ksclient.get_token()
                if token:
                    headers["X-Auth-Token"] = token
                    headers["Content-type"] = "application/json"
                else:
                    warning_string = """Unable to get token. Keystone API
                    server may be down. Skipping check for {0}""".format(addr)
                    self.log.warning(warning_string)
                    return False, warning_string
            try:
                self.log.debug("Connecting to %s" % addr)
                if disable_ssl_validation:
                    self.log.info("Skipping SSL certificate validation for %s based on configuration" % addr)
                h = Http(timeout=timeout, disable_ssl_certificate_validation=disable_ssl_validation)
                if username is not None and password is not None:
                    h.add_credentials(username, password)
                resp, content = h.request(addr, "GET", headers=headers)

            except (socket.timeout, HttpLib2Error, socket.error) as e:
                length = int((time.time() - start) * 1000)
                warn_string = '{0} is DOWN, error: {1}. Connection failed ' \
                              'after {2} ms'.format(addr, repr(e), length)
                self.log.warn(warn_string)
                return False, warn_string

            except httplib.ResponseNotReady as e:
                length = int((time.time() - start) * 1000)
                warn_string = '{0} is DOWN, error: {1}. Network is not ' \
                              'routable after {2} ms'.format(addr, repr(e),
                                                             length)
                self.log.warn(warn_string)
                return False, warn_string

            except Exception as e:
                length = int((time.time() - start) * 1000)
                error_string = '{0} is DOWN, error: {1}. Connection failed after {2} ms'.format(addr, repr(e), length)
                self.log.error(error_string)
                return False, error_string

            if response_time:
                # Stop the timer as early as possible
                running_time = time.time() - start
                self.gauge('http_response_time', running_time, dimensions=dimensions)

            if int(resp.status) >= 400:
                if use_keystone and int(resp.status) == 401:
                    if retry:
                        error_string = '{0} is DOWN, unable to get a valid token to connect with'.format(addr)
                        self.log.error(error_string)
                        return False, error_string
                    else:
                        # Get a new token and retry
                        self.log.info("Token expired, getting new token and retrying...")
                        retry = True
                        ksclient.refresh_token()
                        continue
                else:
                    warn_string = '{0} is DOWN, error code: {1}'.\
                        format(addr, str(resp.status))
                    self.log.warn(warn_string)
                    return False, warn_string
            done = True
            return True, content

    def _check(self, instance):
        addr = instance.get("url", None)
        pattern = instance.get('match_pattern', None)

        dimensions = self._set_dimensions({'url': addr}, instance)

        success, result_string = self._http_check(instance)
        if not success:
            self.gauge('http_status',
                       1,
                       dimensions=dimensions)
            return services_checks.Status.DOWN, result_string

        if pattern is not None:
            if re.search(pattern, result_string, re.DOTALL):
                self.log.debug("Pattern match successful")
            else:
                error_string = 'Pattern match failed! "{0}" not in "{1}"'.format(pattern, result_string)
                self.log.info(error_string)
                self.gauge('http_status',
                           1,
                           dimensions=dimensions,
                           value_meta={'error': error_string[:2048]})
                return services_checks.Status.DOWN, error_string

        success_string = '{0} is UP'.format(addr)
        self.log.debug(success_string)
        self.gauge('http_status', 0, dimensions=dimensions)
        return services_checks.Status.UP, success_string
