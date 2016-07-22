#!/bin/env python
"""Monasca Agent wrapper for Nagios Event Broker module MK Livestatus
   The main difference between this plugin and nagios_wrapper.py is that
   instead of executing Nagios plugins directly, this will query them
   from the Event Broker API using the MK Livestatus module.  This
   solution is faster and less complex, but does require the Livestatus
   plugin be enabled on the host system.  For more information, see
   http://mathias-kettner.de/checkmk_livestatus.html
"""


#    (C) Copyright 2015,2016 Hewlett Packard Enterprise Development Company LP
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import re
import socket
import sys
import time

from monasca_agent.collector.checks import AgentCheck


class WrapMK(AgentCheck):
    """Inherit AgentCheck class to process Nagios checks.

    """

    def __init__(self, name, init_config, agent_config, instances=None):
        AgentCheck.__init__(self, name, init_config, agent_config, instances)

    def check(self, instance):
        """Run the display_name and capture the result.

        """

        dimensions = self._set_dimensions({'observer_host': socket.getfqdn()},
                                          instance)

        # Make the socket connection
        socket_path = self.init_config.get('socket_path')
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            s.connect(socket_path)
        except socket.error, (err):
            self.log.error("Error connecting to {0}: {1}".format(socket_path,
                                                                 str(err)))
            sys.exit(1)

        # Query the requested data
        # "hosts" or "services"
        get = "{0}s".format(instance['check_type'])
        columns = 'last_check host_name {0}state plugin_output'.format(
            'host_' if instance['check_type'] == 'host' else ''
        )
        if instance['check_type'] == 'service':
            columns = "{0} display_name".format(columns)

        # Apply filters, if any
        filters = []
        if 'host_name' in instance:
            filters.append("host_name = {0}".format(instance['host_name']))
        if 'display_name' in instance:
            filters.append("display_name = {0}".format(instance['display_name']))

        if len(filters) > 0:
            filter_list = "\nFilter: ".join(filters)
            s.send("GET {0}\nFilter: {1}\nColumns: {2}\n".format(get,
                                                                 filter_list,
                                                                 columns))
        else:
            s.send("GET {0}\nColumns: {1}\n".format(get, columns))

        # Important: Close sending direction. That way
        # the other side knows we're finished.
        s.shutdown(socket.SHUT_WR)

        # Read the answer
        total_response = []
        while True:
            try:
                response = s.recv(8192)
                if response:
                    total_response.append(response)
                else:
                    time.sleep(0.1)
            except NameError:
                pass
                break

        measurement = {}
        for line in ''.join(total_response).split('\n')[:-1]:
            # Build a dictionary 'measurement' out of column names and output
            for index in range(len(columns.split(' '))):
                measurement[columns.split(' ')[index]] = line.split(';')[index]

            # Build a reasonable metric name from display_name, if not supplied
            metric_name = ""
            if 'name' in instance:
                metric_name = instance['name']
            elif instance['check_type'] == 'service':
                metric_name = re.sub(' ', '_',
                                     "nagios.{0}_status".format(measurement['display_name'].lower()))
            elif instance['check_type'] == 'host':
                metric_name = 'nagios.host_status'

            # Normalize name of measurement state
            if instance['check_type'] == 'host':
                measurement['state'] = measurement['host_state']

            # Set meta tags & extra dimensions
            value_meta = {'detail': measurement['plugin_output'],
                          'last_check': measurement['last_check']}
            dimensions.update({'target_host': measurement['host_name']})

            self.gauge(metric_name, measurement['state'],
                       dimensions=dimensions, value_meta=value_meta)
