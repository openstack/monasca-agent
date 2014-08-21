#!/bin/env python
"""Monitoring Agent remote host aliveness checker.

"""

import socket
import subprocess
import sys

from monagent.collector.checks.services_checks import ServicesCheck
from monagent.collector.checks.services_checks import Status


class HostAlive(ServicesCheck):

    """Inherit ServicesCheck class to test if a host is alive or not.

    """

    def __init__(self, name, init_config, agent_config, instances=None):
        ServicesCheck.__init__(self, name, init_config, agent_config, instances)

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
            self.log.error("Error creating socket: " + str(msg[0]) + msg[1])
            return False

        try:
            host_ip = socket.gethostbyname(host)
        except socket.gaierror:
            self.log.error("Unable to resolve host", host)
            return False

        try:
            sock.connect((host_ip, port))
            banner = sock.recv(1024)
            sock.close()
        except socket.error:
            return False
        if banner.startswith('SSH'):
            return True
        else:
            return False

    @staticmethod
    def _test_ping(host, timeout=None):
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
            ping = subprocess.check_output(ping_command.split(" "), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            return False

        # Look at the output for a packet loss percentage
        if ping.find('100%') > 0:
            return False
        else:
            return True

    def _create_status_event(self, status, msg, instance):
        """Does nothing: status events are not yet supported by Mon API.

        """
        return

    def _check(self, instance):
        """Run the desired host-alive check againt this host.

        """

        dimensions = {'target_host': instance['host_name'], 'observer_host': socket.getfqdn()}
        # Add per-instance dimensions, if any
        if 'dimensions' in instance.keys() and instance['dimensions'] is not None:
            dimensions.update(instance['dimensions'])

        success = False

        if instance['alive_test'] == 'ssh':
            success = self._test_ssh(instance['host_name'],
                                     self.init_config.get('ssh_port'),
                                     self.init_config.get('ssh_timeout'))
        elif instance['alive_test'] == 'ping':
            success = self._test_ping(instance['host_name'],
                                      self.init_config.get('ping_timeout'))
        else:
            self.log.info("Unrecognized alive_test " + instance['alive_test'])

        if success is True:
            self.gauge('host_alive', 0, dimensions=dimensions)
            return Status.UP, "UP"
        else:
            self.gauge('host_alive', 1, dimensions=dimensions)
            self.log.error("Host down: " + instance['host_name'])
            return Status.DOWN, "DOWN"
