#!/bin/env python
# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
"""Monitoring Agent plugin for HTTP/API checks.

"""

import json
from numbers import Number

import monasca_agent.collector.checks.services_checks as services_checks
import monasca_agent.collector.checks_d.http_check as http_check


class HTTPMetrics(http_check.HTTPCheck):

    def __init__(self, name, init_config, agent_config, instances=None):
        super(HTTPMetrics, self).__init__(name, init_config, agent_config,
                                          instances)
        self.metric_method = {
            'gauge': self.gauge,
            'counter': self.increment,
            'rate': self.rate}

    def _valid_number(self, value, name):
        if not isinstance(value, Number):
            self.log.info("Value '{0}' is not a number for metric {1}".format(
                value, name))
            return False
        return True

    def _check(self, instance):
        addr = instance.get("url", None)
        whitelist = instance.get("whitelist", None)

        dimensions = self._set_dimensions({'url': addr}, instance)

        success, result_string = self._http_check(instance)

        if success:
            json_data = json.loads(result_string)

            for metric in whitelist:
                try:
                    metric_name = metric['name']
                    metric_type = metric['type']
                    keys = metric['path'].split('/')
                except Exception:
                    self.log.warning("Invalid configuration for metric '{0}'".format(metric))
                    continue

                current = json_data
                try:
                    for key in keys:
                        current = current[key]
                except Exception:
                    self.log.warning("Could not find a value at {0} in json message".format(keys))
                    continue

                value = current

                # everything requires a number
                if metric_type in ['gauge', 'counter', 'rate']:
                    if not self._valid_number(value, metric_name):
                        self.log.warning("Invalid value '{0}' for metric '{1}'".format(value, metric_name))
                        continue

                if metric_type in self.metric_method:
                    self.metric_method[metric_type](metric_name,
                                                    value,
                                                    dimensions=dimensions)
                else:
                    self.log.warning("Unrecognized type '{0}' for metric '{1}'".format(metric_type, metric_name))

            success_string = '{0} is UP'.format(addr)
            self.log.debug(success_string)
            return services_checks.Status.UP, success_string
