# (C) Copyright 2015-2017 Hewlett Packard Enterprise Development LP
"""Base class for Checks.

If you are writing your own checks you should subclass the AgentCheck class.
The Check class is being deprecated so don't write new checks with it.
"""
# This file uses 'print' as a function rather than a statement, a la Python3
from __future__ import print_function

import logging
import os
import re

import yaml

import monasca_agent.common.aggregator as aggregator
import monasca_agent.common.metrics as metrics_pkg
import monasca_agent.common.util as util


class AgentCheck(util.Dimensions):

    def __init__(self, name, init_config, agent_config, instances=None):
        """Initialize a new check.

        :param name: The name of the check
        :param init_config: The config for initializing the check
        :param agent_config: The global configuration for the agent
        :param instances: A list of configuration objects for each instance.
        """
        super(AgentCheck, self).__init__(agent_config)
        self.name = name
        self.init_config = init_config
        self.white_list = init_config.get('white_list', None)
        self.hostname = util.get_hostname()
        self.log = logging.getLogger('%s.%s' % (__name__, name))
        threshold = agent_config.get('recent_point_threshold', None)
        tenant_id = agent_config.get('global_delegated_tenant', None)
        self.aggregator = (
            aggregator.MetricsAggregator(self.hostname,
                                         recent_point_threshold=threshold,
                                         tenant_id=tenant_id))

        self.instances = instances or []
        self.library_versions = None

    def instance_count(self):
        """Return the number of instances that are configured for this check.
        """
        return len(self.instances)

    def submit_metric(self, metric, value, metric_type, dimensions,
                      delegated_tenant, hostname, device_name, value_meta,
                      timestamp=None):
        # If there is no white list, then report all the metrics
        dimensions_white_list = dimensions.copy()
        if self.white_list:
            if 'metrics' not in self.white_list.keys():
                return
            else:
                metrics = self.white_list['metrics']
                if metric not in metrics:
                    return
                # If there is a white list, then only report the metrics listed
                # in white list. Also check if there are dimension key value
                # pairs specified in the metrics section of white list, if
                # there is make sure the keys are in dimensions before
                # submitting the metric. If not, set to the corresponding
                # value in white list.
                dim_key_values = {}
                if metrics.get(metric):
                    dim_key_values = metrics.get(metric).values()[0]
                else:
                    # If white list has a "dimensions" section, set the key
                    # value dimension pairs to all the metrics. But the
                    # dimensions under "metrics" section has higher priority.
                    if 'dimensions' in self.white_list.keys():
                        dim_key_values = self.white_list['dimensions']
                for dim_kv in dim_key_values.items():
                    if dim_kv[0] not in dimensions_white_list.keys():
                        dimensions_white_list[dim_kv[0]] = dim_kv[1]
        try:
            self.aggregator.submit_metric(metric,
                                          value,
                                          metric_type,
                                          dimensions_white_list,
                                          delegated_tenant,
                                          hostname,
                                          device_name,
                                          value_meta,
                                          timestamp)
        except Exception as e:
            self.log.exception("invalid metric: {}".format(e))

    def gauge(self, metric, value, dimensions=None, delegated_tenant=None, hostname=None,
              device_name=None, timestamp=None, value_meta=None):
        """Record the value of a gauge, with optional dimensions, hostname, value metadata and device name.

        :param metric: The name of the metric
        :param value: The value of the gauge
        :param dimensions: (optional) A dictionary of dimensions for this metric
        :param delegated_tenant: (optional) Submit metrics on behalf of this tenant ID.
        :param hostname: (optional) A hostname for this metric. Defaults to the current hostname.
        :param device_name: (optional) The device name for this metric
        :param timestamp: (optional) The timestamp for this metric value
        :param value_meta: Additional metadata about this value
        """
        self.submit_metric(metric,
                           value,
                           metrics_pkg.Gauge,
                           dimensions,
                           delegated_tenant,
                           hostname,
                           device_name,
                           value_meta,
                           timestamp)

    def increment(self, metric, value=1, dimensions=None, delegated_tenant=None,
                  hostname=None, device_name=None, value_meta=None):
        """Increment a counter with optional dimensions, hostname and device name.

        :param metric: The name of the metric
        :param value: The value to increment by
        :param dimensions: (optional) A dictionary of dimensions for this metric
        :param delegated_tenant: (optional) Submit metrics on behalf of this tenant ID.
        :param hostname: (optional) A hostname for this metric. Defaults to the current hostname.
        :param device_name: (optional) The device name for this metric
        :param value_meta: Additional metadata about this value
        """
        self.submit_metric(metric,
                           value,
                           metrics_pkg.Counter,
                           dimensions,
                           delegated_tenant,
                           hostname,
                           device_name,
                           value_meta)

    def decrement(self, metric, value=1, dimensions=None, delegated_tenant=None,
                  hostname=None, device_name=None, value_meta=None):
        """Decrement a counter with optional dimensions, hostname and device name.

        :param metric: The name of the metric
        :param value: The value to decrement by
        :param dimensions: (optional) A dictionary of dimensions for this metric
        :param delegated_tenant: (optional) Submit metrics on behalf of this tenant ID.
        :param hostname: (optional) A hostname for this metric. Defaults to the current hostname.
        :param device_name: (optional) The device name for this metric
        :param value_meta: Additional metadata about this value
        """
        value *= -1
        self.submit_metric(metric,
                           value,
                           metrics_pkg.Counter,
                           dimensions,
                           delegated_tenant,
                           hostname,
                           device_name,
                           value_meta)

    def rate(self, metric, value, dimensions=None, delegated_tenant=None,
             hostname=None, device_name=None, value_meta=None):
        """Submit a point for a metric that will be calculated as a rate on flush.

        Values will persist across each call to `check` if there is not enough
        point to generate a rate on the flush.

        :param metric: The name of the metric
        :param value: The value of the rate
        :param dimensions: (optional) A dictionary of dimensions for this metric
        :param delegated_tenant: (optional) Submit metrics on behalf of this tenant ID.
        :param hostname: (optional) A hostname for this metric. Defaults to the current hostname.
        :param device_name: (optional) The device name for this metric
        :param value_meta: Additional metadata about this value
        """
        self.submit_metric(metric,
                           value,
                           metrics_pkg.Rate,
                           dimensions,
                           delegated_tenant,
                           hostname,
                           device_name,
                           value_meta)

    def get_metrics(self, prettyprint=False):
        """Get all metrics, including the ones that are tagged.

        @return the list of samples
        @rtype list of Measurement objects from monasca_agent.common.metrics
        """
        metrics = self.aggregator.flush()
        if prettyprint:
            for metric in metrics:
                measurement = metric['measurement']
                print(" Timestamp: {0}".format(measurement['timestamp']))
                print(" Name:       {0}".format(measurement['name']))
                print(" Value:      {0}".format(measurement['value']))
                print(" Dimensions: ", end='')
                line = 0
                dimensions = measurement['dimensions']
                for name in dimensions:
                    if line != 0:
                        print(" " * 13, end='')
                    print("{0}={1}".format(name, dimensions[name]))
                    line += 1

                print(" Value Meta: ", end='')
                value_meta = measurement['value_meta']
                if value_meta:
                    line = 0
                    for name in value_meta:
                        if line != 0:
                            print(" " * 13, end='')
                        print("{0}={1}".format(name, value_meta[name]))
                        line += 1
                else:
                    print('None')
                print("-" * 24)

        return metrics

    def get_library_info(self):
        if self.library_versions is not None:
            return self.library_versions
        try:
            self.library_versions = self.get_library_versions()
        except NotImplementedError:
            pass

    def get_library_versions(self):
        """Should return a string that shows which version

        of the needed libraries are used
        """
        raise NotImplementedError

    def prepare_run(self):
        """Do any setup required before running all instances"""
        return

    def run(self):
        """Run all instances.
        """
        self.prepare_run()

        for i, instance in enumerate(self.instances):
            try:
                self.check(instance)
            except Exception:
                self.log.exception("Check '%s' instance #%s failed" % (self.name, i))

    def check(self, instance):
        """Overriden by the check class. This will be called to run the check.

        :param instance: A dict with the instance information. This will vary
        depending on your config structure.
        """
        raise NotImplementedError()

    def stop(self):
        """To be executed when the agent is being stopped to clean resources.
        """
        pass

    @classmethod
    def from_yaml(cls, path_to_yaml=None, agentConfig=None, yaml_text=None, check_name=None):
        """A method used for testing your check without running the agent.
        """

        if path_to_yaml:
            check_name = os.path.basename(path_to_yaml).split('.')[0]
            try:
                f = open(path_to_yaml)
            except IOError:
                raise Exception('Unable to open yaml config: %s' % path_to_yaml)
            yaml_text = f.read()
            f.close()

        config = yaml.safe_load(yaml_text)
        check = cls(check_name, config.get('init_config') or {}, agentConfig or {})

        return check, config.get('instances', [])

    @staticmethod
    def normalize(metric, prefix=None):
        """Turn a metric into a well-formed metric name prefix.b.c

        :param metric The metric name to normalize
        :param prefix A prefix to to add to the normalized name, default None
        """
        name = re.sub(r"[,\+\*\-/()\[\]{}]", "_", metric)
        # Eliminate multiple _
        name = re.sub(r"__+", "_", name)
        # Don't start/end with _
        name = re.sub(r"^_", "", name)
        name = re.sub(r"_$", "", name)
        # Drop ._ and _.
        name = re.sub(r"\._", ".", name)
        name = re.sub(r"_\.", ".", name)

        if prefix is not None:
            return prefix + "." + name
        else:
            return name

    @staticmethod
    def read_config(instance, key, message=None, cast=None, optional=False):
        val = instance.get(key)
        if val is None:
            if optional is False:
                message = message or 'Must provide `%s` value in instance config' % key
                raise Exception(message)
            else:
                return val

        if cast is None:
            return val
        else:
            return cast(val)
