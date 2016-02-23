#!/bin/env python
"""Monasca Agent plugin for Check_MK agent
   This plugin will query the Check_MK agent, extracting and publishing
   metrics for all configured local checks, except where configured to discard.
   See check_mk_local.yaml.example for configuration.  For more on Check_MK,
   see http://mathias-kettner.com/checkmk_localchecks.html
"""

# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

import os

from monasca_agent.collector.checks import AgentCheck


class CheckMK(AgentCheck):
    """Inherit AgentCheck class to process Check_MK checks.
    """

    def __init__(self, name, init_config, agent_config, instances=None):
        AgentCheck.__init__(self, name, init_config, agent_config, instances)

    def check(self, instance):
        """Run check_mk_agent and process the '<<<local>>>' results.
        """

        local = False
        # Run check_mk_agent (in a way compatible with Python 2.6)
        for line in os.popen(self.init_config.get('mk_agent_path')).readlines():
            if local:
                metric_name = None
                dimensions = self._set_dimensions(None, instance)

                # <<<local>>> lines use the following format, space-delimited
                # for the first three fields, then free-form for the fourth:
                # [Status] [Item Name] [Performance data] [Check output]
                check_data = line.split(' ')

                # Look for any custom configuration for this check
                if 'custom' in self.init_config and self.init_config['custom']:
                    custom = filter(lambda d: d['mk_item'] == check_data[1],
                                    self.init_config.get('custom'))
                    if len(custom) > 0:
                        if 'discard' in custom[0] and custom[0]['discard']:
                            continue

                        if 'dimensions' in custom[0]:
                            dimensions = self._set_dimensions(custom[0]['dimensions'],
                                                              instance)
                        if 'metric_name_base' in custom[0]:
                            metric_name = custom[0]['metric_name_base']

                value_meta = {'detail': ' '.join(check_data[3:])}

                # Build a reasonable metric name, if not already configured
                if metric_name is None:
                    metric_name = "check_mk.{0}".format(check_data[1].lower())

                # Send 'status' metric
                self.gauge("{0}.status".format(metric_name), check_data[0],
                           dimensions, value_meta=value_meta)

                # Send performance measurements as separate metrics.  Multiple
                # measurements are separated by a pipe (|) character, and the
                # the value of an individual measurement may contain a list
                # of numbers delmited by semicolons: value;warn;crit;min;max.
                # We will only use the first field, the 'value' field.
                for perf in check_data[2].split('|'):
                    try:
                        measurement = perf.split('=')
                        if len(measurement[1]):
                            self.gauge("{0}.{1}".format(metric_name,
                                                        measurement[0]),
                                       measurement[1].split(';')[0],
                                       dimensions)
                    except IndexError:
                        # Performance field is not well-formed, discard it
                        pass
            else:
                # The '<<<local>>>' section is at the end of the output.  Once
                # reaching this point, process all lines for metrics.
                if line.startswith('<<<local>>>'):
                    local = True
