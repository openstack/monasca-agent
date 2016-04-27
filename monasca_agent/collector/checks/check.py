# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development Company LP
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
        self.hostname = util.get_hostname()
        self.log = logging.getLogger('%s.%s' % (__name__, name))

        threshold = agent_config.get('recent_point_threshold', None)
        self.aggregator = (
            aggregator.MetricsAggregator(self.hostname,
                                         recent_point_threshold=threshold))

        self.events = []
        self.instances = instances or []
        self.library_versions = None

    def instance_count(self):
        """Return the number of instances that are configured for this check.
        """
        return len(self.instances)

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
        self.aggregator.submit_metric(metric,
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
        self.aggregator.submit_metric(metric,
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
        self.aggregator.submit_metric(metric,
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
        self.aggregator.submit_metric(metric,
                                      value,
                                      metrics_pkg.Rate,
                                      dimensions,
                                      delegated_tenant,
                                      hostname,
                                      device_name,
                                      value_meta)

    def histogram(self, metric, value, dimensions=None, delegated_tenant=None,
                  hostname=None, device_name=None, value_meta=None):
        """Sample a histogram value, with optional dimensions, hostname and device name.

        :param metric: The name of the metric
        :param value: The value to sample for the histogram
        :param dimensions: (optional) A dictionary of dimensions for this metric
        :param delegated_tenant: (optional) Submit metrics on behalf of this tenant ID.
        :param hostname: (optional) A hostname for this metric. Defaults to the current hostname.
        :param device_name: (optional) The device name for this metric
        :param value_meta: Additional metadata about this value
        """
        self.aggregator.submit_metric(metric,
                                      value,
                                      metrics_pkg.Histogram,
                                      dimensions,
                                      delegated_tenant,
                                      hostname,
                                      device_name,
                                      value_meta)

    def set(self, metric, value, dimensions=None, delegated_tenant=None,
            hostname=None, device_name=None, value_meta=None):
        """Sample a set value, with optional dimensions, hostname and device name.

        :param metric: The name of the metric
        :param value: The value for the set
        :param dimensions: (optional) A dictionary of dimensions for this metric
        :param delegated_tenant: (optional) Submit metrics on behalf of this tenant ID.
        :param hostname: (optional) A hostname for this metric. Defaults to the current hostname.
        :param device_name: (optional) The device name for this metric
        :param value_meta: Additional metadata about this value
        """
        self.aggregator.submit_metric(metric,
                                      value,
                                      metrics_pkg.Set,
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
                print(" Timestamp:  {0}".format(metric.timestamp))
                print(" Name:       {0}".format(metric.name))
                print(" Value:      {0}".format(metric.value))
                if (metric.delegated_tenant):
                    print(" Delegate ID: {0}".format(metric.delegated_tenant))

                print(" Dimensions: ", end='')
                line = 0
                for name in metric.dimensions:
                    if line != 0:
                        print(" " * 13, end='')
                    print("{0}={1}".format(name, metric.dimensions[name]))
                    line += 1

                print(" Value Meta: ", end='')
                if metric.value_meta:
                    line = 0
                    for name in metric.value_meta:
                        if line != 0:
                            print(" " * 13, end='')
                        print("{0}={1}".format(name, metric.value_meta[name]))
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

    @staticmethod
    def stop():
        """To be executed when the agent is being stopped to clean resources.
        """
        pass

    @classmethod
    def from_yaml(cls, path_to_yaml=None, agentConfig=None, yaml_text=None, check_name=None):
        """A method used for testing your check without running the agent.
        """
        if hasattr(yaml, 'CLoader'):
            Loader = yaml.CLoader
        else:
            Loader = yaml.Loader

        if path_to_yaml:
            check_name = os.path.basename(path_to_yaml).split('.')[0]
            try:
                f = open(path_to_yaml)
            except IOError:
                raise Exception('Unable to open yaml config: %s' % path_to_yaml)
            yaml_text = f.read()
            f.close()

        config = yaml.load(yaml_text, Loader=Loader)
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
