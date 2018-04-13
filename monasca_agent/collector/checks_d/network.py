# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

# stdlib
import logging
import psutil
import re

# project
import monasca_agent.collector.checks as checks

log = logging.getLogger(__name__)


class Network(checks.AgentCheck):

    def __init__(self, name, init_config, agent_config):
        super(Network, self).__init__(name, init_config, agent_config)

    def check(self, instance):
        """Capture network metrics

        """
        dimensions = self._set_dimensions(None, instance)

        excluded_ifaces = instance.get('excluded_interfaces', [])
        if excluded_ifaces:
            log.debug('Excluding network devices: {0}'.format(excluded_ifaces))

        exclude_re = instance.get('excluded_interface_re', None)
        if exclude_re:
            exclude_iface_re = re.compile(exclude_re)
            log.debug('Excluding network devices matching: {0}'.format(exclude_re))
        else:
            exclude_iface_re = None

        nics = psutil.net_io_counters(pernic=True)
        for nic_name in nics.keys():
            if self._is_nic_monitored(nic_name, excluded_ifaces, exclude_iface_re):
                nic = nics[nic_name]
                if instance.get('use_bits'):
                    self.rate(
                        'net.in_bits_sec',
                        nic.bytes_recv * 8,
                        device_name=nic_name,
                        dimensions=dimensions)
                    self.rate(
                        'net.out_bits_sec',
                        nic.bytes_sent * 8,
                        device_name=nic_name,
                        dimensions=dimensions)
                else:
                    self.rate(
                        'net.in_bytes_sec',
                        nic.bytes_recv,
                        device_name=nic_name,
                        dimensions=dimensions)
                    self.rate(
                        'net.out_bytes_sec',
                        nic.bytes_sent,
                        device_name=nic_name,
                        dimensions=dimensions)
                if instance.get('net_bytes_only'):
                    continue
                self.rate(
                    'net.in_packets_sec',
                    nic.packets_recv,
                    device_name=nic_name,
                    dimensions=dimensions)
                self.rate(
                    'net.out_packets_sec',
                    nic.packets_sent,
                    device_name=nic_name,
                    dimensions=dimensions)
                self.rate(
                    'net.in_errors_sec',
                    nic.errin,
                    device_name=nic_name,
                    dimensions=dimensions)
                self.rate(
                    'net.out_errors_sec',
                    nic.errout,
                    device_name=nic_name,
                    dimensions=dimensions)
                self.rate(
                    'net.in_packets_dropped_sec',
                    nic.dropin,
                    device_name=nic_name,
                    dimensions=dimensions)
                self.rate(
                    'net.out_packets_dropped_sec',
                    nic.dropout,
                    device_name=nic_name,
                    dimensions=dimensions)

                log.debug('Collected 8 network metrics for device {0}'.format(nic_name))

        nic_stats = psutil.net_if_stats()
        for nic_name in nic_stats.keys():
            if self._is_nic_monitored(nic_name, excluded_ifaces, exclude_iface_re):
                nic = nic_stats[nic_name]
                if nic.isup:
                    self.gauge('net.int_status', 0, device_name=nic_name, dimensions=dimensions)
                else:
                    self.gauge('net.int_status', 1, device_name=nic_name, dimensions=dimensions)

                log.debug('Collected network interface status for device {0}'.format(nic_name))

    def _is_nic_monitored(self, nic_name, excluded_ifaces, exclude_iface_re):
        if nic_name in excluded_ifaces:
            return False
        if exclude_iface_re and exclude_iface_re.match(nic_name):
            return False
        return True
