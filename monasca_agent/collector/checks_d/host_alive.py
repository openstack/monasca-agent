#!/bin/env python
# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development LP
"""Monitoring Agent remote host aliveness checker.

"""

import socket
import subprocess
import sys

import monasca_agent.collector.checks.services_checks as services_checks
import monasca_agent.common.util as util


class HostAlive(services_checks.ServicesCheck):

    """Inherit ServicesCheck class to test if a host is alive or not.

    """

    def __init__(self, name, init_config, agent_config, instances=None):
        super(HostAlive, self).__init__(name, init_config, agent_config, instances)

    def _test_ssh(self, host, port, timeout=None):
        """Connect to the SSH port (typically 22) and look for a banner.

        """
        if port is None:
            port = 22
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if timeout is not None:
                sock.settimeout(timeout)
        except socket.error as msg:
            error_message = 'Error creating socket: {0}'.format(str(msg[0]) + msg[1])
            self.log.warn(error_message)
            return False, error_message

        try:
            host_ip = socket.gethostbyname(host)
        except socket.gaierror:
            error_message = 'Unable to resolve host {0}'.format(host)
            self.log.warn(error_message)
            return False, error_message

        try:
            sock.connect((host_ip, port))
            banner = sock.recv(1024)
            sock.close()
        except socket.error:
            error_message = 'Unable to open socket to host {0}'.format(host)
            self.log.warn(error_message)
            return False, error_message
        if banner.startswith('SSH'):
            return True, None
        else:
            error_message = 'Unexpected response "{0}" from host {1}'.format(banner, host)
            self.log.warn(error_message)
            return False, error_message

    def _test_ping(self, host, timeout=None):
        """Attempt to ping the host.

        """
        ping_prefix = "ping -c 1 -q "
        if timeout is not None:
            ping_prefix += "-W " + str(timeout) + " "
        if sys.platform.startswith('win'):
            ping_prefix = "ping -n 1 "
            if timeout is not None:
                # On Windows, timeout is in milliseconds
                timeout *= 1000
                ping_prefix += "-w " + str(timeout) + " "
        ping_command = ping_prefix + host

        try:
            subprocess.check_output(ping_command.split(" "), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            error_message = 'Host not accessible, ping test failed ("{0}")'.format(ping_command)
            self.log.info(error_message)
            return False, error_message
        except OSError as err:
            error_message = 'ping command "{0}" failed to run: {1}'.format(ping_command, err)
            self.log.warn(error_message)
            return False, error_message
        return True, None

    def _check(self, instance):
        """Run the desired host-alive check against this host.

        """

        host_name = instance.get('host_name', None)
        if not host_name:
            raise ValueError('host_name not specified!')

        # Allow a different network name to be used for the check
        # to handle multi-homed systems
        if instance.get('target_hostname', None):
            target_hostname = instance.get('target_hostname')
        else:
            target_hostname = host_name

        host_dimensions = {'hostname': host_name, 'observer_host': util.get_hostname()}
        # If the check is against a different network name than host_name, add it to
        # the dimensions
        if target_hostname != host_name:
            host_dimensions['target_hostname'] = target_hostname

        dimensions = self._set_dimensions(host_dimensions,
                                          instance)

        success = False
        test_type = instance['alive_test']
        if test_type == 'ssh':
            success, error_message = self._test_ssh(target_hostname,
                                                    self.init_config.get('ssh_port'),
                                                    self.init_config.get('ssh_timeout'))
        elif test_type == 'ping':
            success, error_message = self._test_ping(target_hostname,
                                                     self.init_config.get('ping_timeout'))
        else:
            error_message = 'Unrecognized alive_test: {0}'.format(test_type)

        dimensions.update({'test_type': test_type})
        if success is True:
            self.gauge('host_alive_status',
                       0,
                       dimensions=dimensions)
            return services_checks.Status.UP, "UP"
        else:
            self.gauge('host_alive_status',
                       1,
                       dimensions=dimensions,
                       value_meta={'error': error_message})
            return services_checks.Status.DOWN, "DOWN"
