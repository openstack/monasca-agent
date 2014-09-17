#!/bin/env python
"""Monitoring Agent plugin for HTTP/API checks.

"""

import json
import re
import socket
import time

from httplib2 import Http
from httplib2 import httplib
from httplib2 import HttpLib2Error

from monagent.collector.checks.check import AgentCheck
from monagent.collector.checks.services_checks import ServicesCheck
from monagent.collector.checks.services_checks import Status


class HTTPCheck(ServicesCheck):

    def __init__(self, name, init_config, agent_config, instances=None):
        super(HTTPCheck, self).__init__(name, init_config, agent_config, instances)

    @staticmethod
    def _load_conf(instance):
        # Fetches the conf
        dimensions = instance.get('dimensions', {})
        username = instance.get('username', None)
        password = instance.get('password', None)
        timeout = int(instance.get('timeout', 10))
        headers = instance.get('headers', {})
        use_keystone = instance.get('use_keystone', False)
        url = instance.get('url', None)
        response_time = instance.get('collect_response_time', False)
        pattern = instance.get('match_pattern', None)
        if url is None:
            raise Exception("Bad configuration. You must specify a url")
        ssl = instance.get('disable_ssl_validation', True)
        token = AgentCheck.keystone.get_token()

        return url, username, password, timeout, headers, response_time, dimensions, ssl, pattern, use_keystone, token

    def _create_status_event(self, status, msg, instance):
        """Does nothing: status events are not yet supported by Mon API.

        """
        return

    def _check(self, instance):
        addr, username, password, timeout, headers, response_time, dimensions, disable_ssl_validation, pattern, use_keystone, token = self._load_conf(
            instance)

        content = ''

        new_dimensions = dimensions.copy()
        if dimensions is not None:
            new_dimensions.update(dimensions)
        new_dimensions['url'] = addr

        start = time.time()
        done = False
        retry = False
        while not done or retry:
            if use_keystone:
                if token:
                    headers["X-Auth-Token"] = token
                    headers["Content-type"] = "application/json"
                else:
                    self.log.warning("Unable to get token, skipping check...")
                    return
            try:
                self.log.debug("Connecting to %s" % addr)
                if disable_ssl_validation:
                    self.warning(
                        "Skipping SSL certificate validation for %s based on configuration" % addr)
                h = Http(timeout=timeout, disable_ssl_certificate_validation=disable_ssl_validation)
                if username is not None and password is not None:
                    h.add_credentials(username, password)
                resp, content = h.request(addr, "GET", headers=headers)

            except socket.timeout as e:
                length = int((time.time() - start) * 1000)
                self.log.info(
                    "%s is DOWN, error: %s. Connection failed after %s ms" % (addr, str(e), length))
                self.gauge('http_status', 1, dimensions=new_dimensions)
                return Status.DOWN, "%s is DOWN, error: %s. Connection failed after %s ms" % (
                    addr, str(e), length)

            except HttpLib2Error as e:
                length = int((time.time() - start) * 1000)
                self.log.info(
                    "%s is DOWN, error: %s. Connection failed after %s ms" % (addr, str(e), length))
                self.gauge('http_status', 1, dimensions=new_dimensions)
                return Status.DOWN, "%s is DOWN, error: %s. Connection failed after %s ms" % (
                    addr, str(e), length)

            except socket.error as e:
                length = int((time.time() - start) * 1000)
                self.log.info("%s is DOWN, error: %s. Connection failed after %s ms" % (
                    addr, repr(e), length))
                self.gauge('http_status', 1, dimensions=new_dimensions)
                return Status.DOWN, "%s is DOWN, error: %s. Connection failed after %s ms" % (
                    addr, str(e), length)

            except httplib.ResponseNotReady as e:
                length = int((time.time() - start) * 1000)
                self.log.info("%s is DOWN, error: %s. Network is not routable after %s ms" % (
                    addr, repr(e), length))
                self.gauge('http_status', 1, dimensions=new_dimensions)
                return Status.DOWN, "%s is DOWN, error: %s. Network is not routable after %s ms" % (
                    addr, str(e), length)

            except Exception as e:
                length = int((time.time() - start) * 1000)
                self.log.error(
                    "Unhandled exception %s. Connection failed after %s ms" % (str(e), length))
                self.gauge('http_status', 1, dimensions=new_dimensions)
                return Status.DOWN, "%s is DOWN, error: %s. Connection failed after %s ms" % (
                    addr, str(e), length)

            if response_time:
                # Stop the timer as early as possible
                running_time = time.time() - start
                self.gauge('http_response_time', running_time, dimensions=new_dimensions)

            # TODO(dschroeder): Save/send content data when supported by API

            if int(resp.status) >= 400:
                if use_keystone and int(resp.status) == 401:
                    if retry:
                        return Status.DOWN, "%s is DOWN, unable to get a valid token to connect with" % (
                            addr)
                    else:
                        # Get a new token and retry
                        self.log.warning("Token expired, getting new token and retrying...")
                        HTTPCheck.token = self.keystone.refresh_token()
                        retry = True
                        continue
                else:
                    self.log.info("%s is DOWN, error code: %s" % (addr, str(resp.status)))
                    self.gauge('http_status', 1, dimensions=new_dimensions)
                    return Status.DOWN, "%s is DOWN, error code: %s" % (addr, str(resp.status))

            if pattern is not None:
                if re.search(pattern, content, re.DOTALL):
                    self.log.debug("Pattern match successful")
                else:
                    self.log.info("Pattern match failed! '%s' not in '%s'" % (pattern, content))
                    self.gauge('http_status', 1, dimensions=new_dimensions)
                    return Status.DOWN, "Pattern match failed! '%s' not in '%s'" % (
                        pattern, content)

            self.log.debug("%s is UP" % addr)
            self.gauge('http_status', 0, dimensions=new_dimensions)
            done = True
            return Status.UP, "%s is UP" % addr
