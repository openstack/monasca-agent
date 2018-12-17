#!/bin/env python
# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Monitoring Agent plugin for HTTP/API checks.

"""

import os
import re
import socket
import sys
import time

from httplib2 import Http
from httplib2 import HttpLib2Error
from six.moves import http_client

import monasca_agent.collector.checks.services_checks as services_checks
import monasca_agent.common.config as cfg
import monasca_agent.common.keystone as keystone


class HTTPCheck(services_checks.ServicesCheck):

    def __init__(self, name, init_config, agent_config, instances=None):
        self._socket_errors = set()
        self._response_not_ready = set()
        self._general_exception = set()
        self._invalid_token = set()
        self._warn_msg = set()

        super(HTTPCheck, self).__init__(name, init_config, agent_config,
                                        instances)
        # init the keystone client if instance has use_keystone
        self._api_config = cfg.Config().get_config('Api')
        self._ksclients = {}

        init_keystone_config = init_config.get('keystone_config', None)

        for instance in instances:
            addr, username, password, timeout, headers, response_time, \
                disable_ssl_validation, use_keystone, keystone_config, \
                instance_name = self._load_http_conf(instance)
            if use_keystone:
                # keystone is a singleton. It will be initialized once,
                # the first config instance used.
                if init_keystone_config:
                    ksclient = keystone.Keystone(init_keystone_config)
                elif keystone_config:
                    # Using Keystone config in each instance is deprecated
                    # in Rocky.
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
                    error_msg = "Unable to get token. Keystone API server may be down."
                    warn_string = '{0} Skipping check for {1}'.format(error_msg, addr)
                    self.log.warning(warn_string)
                    return False, error_msg
            try:
                self.log.debug("Connecting to %s" % addr)
                if disable_ssl_validation:
                    self.log.info(
                        "Skipping SSL certificate validation for %s based on configuration" %
                        addr)
                h = Http(timeout=timeout, disable_ssl_certificate_validation=disable_ssl_validation)
                if username is not None and password is not None:
                    h.add_credentials(username, password)
                resp, content = h.request(addr, "GET", headers=headers)

            except (socket.timeout, HttpLib2Error, socket.error) as e:
                length = int((time.time() - start) * 1000)
                error_msg = 'error: {0}. Connection failed after {1} ' \
                            'ms'.format(repr(e), length)
                if addr not in self._socket_errors:
                    self._socket_errors.add(addr)
                    warn_string = '{0} is DOWN, {1}'.format(addr, error_msg)
                    self.log.warn(warn_string)
                return False, error_msg

            except http_client.ResponseNotReady as e:
                length = int((time.time() - start) * 1000)
                error_msg = 'error: {0}. Network is not routable after {1} ' \
                            'ms'.format(repr(e), length)
                if addr not in self._response_not_ready:
                    self._response_not_ready.add(addr)
                    warn_string = '{0} is DOWN, {1}'.format(addr, error_msg)
                    self.log.warn(warn_string)
                return False, error_msg

            except Exception as e:
                length = int((time.time() - start) * 1000)
                error_msg = 'error: {0}. Connection failed after {1} ms'.format(repr(e), length)
                if addr not in self._general_exception:
                    self._general_exception.add(addr)
                    error_string = '{0} is DOWN, {1}'.format(addr, error_msg)
                    self.log.error(error_string)
                return False, error_msg

            if response_time:
                # Stop the timer as early as possible
                running_time = time.time() - start
                self.gauge('http_response_time', running_time, dimensions=dimensions)

            if int(resp.status) >= 400:
                if use_keystone and int(resp.status) == 401:
                    if retry:
                        error_msg = 'unable to get a valid token to connect with'
                        if addr not in self._invalid_token:
                            self._invalid_token.add(addr)
                            error_string = '{0} is DOWN, {1}'.format(addr, error_msg)
                            self.log.error(error_string)
                        return False, error_msg
                    else:
                        # Get a new token and retry
                        self.log.info("Token expired, getting new token and retrying...")
                        retry = True
                        ksclient.refresh_token()
                        continue
                else:
                    warn_msg = 'error code: {0}'.format(str(resp.status))
                    if addr not in self._warn_msg:
                        self._warn_msg.add(addr)
                        warn_string = '{0} is DOWN, {1}'.format(addr, warn_msg)
                        self.log.warn(warn_string)
                    return False, warn_msg

            self._socket_errors.discard(addr)
            self._invalid_token.discard(addr)
            self._response_not_ready.discard(addr)
            self._general_exception.discard(addr)
            self._warn_msg.discard(addr)

            done = True
            return True, content

    def _check(self, instance):
        addr = instance.get("url", None)
        pattern = instance.get('match_pattern', None)

        dimensions = self._set_dimensions({'url': addr}, instance)

        success, result_string = self._http_check(instance)
        if not success:
            # maximum length of value_meta including {'error':''} is 2048
            # Cutting it down to 1024 here so we don't clutter the
            # database too much.
            self.gauge('http_status',
                       1,
                       dimensions=dimensions,
                       value_meta={'error': result_string[:1024]})
            return services_checks.Status.DOWN, result_string

        if pattern is not None:
            if re.search(pattern, result_string, re.DOTALL):
                self.log.debug("Pattern match successful")
            else:
                error_string = 'Pattern match failed! "{0}" not in "{1}"'.format(
                    pattern, result_string)
                self.log.info(error_string)
                # maximum length of value_meta including {'error':''} is 2048
                # Cutting it down to 1024 here so we don't clutter the
                # database too much.
                self.gauge('http_status',
                           1,
                           dimensions=dimensions,
                           value_meta={'error': error_string[:1024]})
                return services_checks.Status.DOWN, error_string

        success_string = '{0} is UP'.format(addr)
        self.log.debug(success_string)
        self.gauge('http_status', 0, dimensions=dimensions)
        return services_checks.Status.UP, success_string
