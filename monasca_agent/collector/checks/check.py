"""Base class for Checks.

If you are writing your own checks you should subclass the AgentCheck class.
The Check class is being deprecated so don't write new checks with it.
"""
# This file uses 'print' as a function rather than a statement, a la Python3
from __future__ import print_function

import logging
import os
import pprint
import re
import time
import traceback

import yaml

import monasca_agent.common.aggregator as aggregator
import monasca_agent.common.check_status as check_status
import monasca_agent.common.exceptions as exceptions
import monasca_agent.common.util as util


# todo convert all checks to the new interface then remove this and Laconic filter which isn't used elsewhere
# =============================================================================
# DEPRECATED
# ------------------------------
# If you are writing your own check, you should inherit from AgentCheck
# and not this class. This class will be removed in a future version
# of the agent and is currently only used for Windows.
# =============================================================================
class Check(util.Dimensions):

    """(Abstract) class for all checks with the ability to:

    * store 1 (and only 1) sample for gauges per metric/dimensions combination
    * compute rates for counters
    * only log error messages once (instead of each time they occur)
    """

    def __init__(self, logger, agent_config=None):
        # where to store samples, indexed by metric_name
        # metric_name: {("sorted", "dimensions"): [(ts, value), (ts, value)],
        #                 tuple(dimensions) are stored as a key since lists are not hashable
        #               None: [(ts, value), (ts, value)]}
        #                 untagged values are indexed by None
        super(Check, self).__init__(agent_config)
        self._sample_store = {}
        self._counters = {}  # metric_name: bool
        self.logger = logger
        try:
            self.logger.addFilter(util.LaconicFilter())
        except Exception:
            self.logger.exception("Trying to install laconic log filter and failed")

    @staticmethod
    def normalize(metric, prefix=None):
        """Turn a metric into a well-formed metric name

        prefix.b.c
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
    def normalize_device_name(device_name):
        return device_name.strip().lower().replace(' ', '_')

    def counter(self, metric):
        """Treats the metric as a counter, i.e. computes its per second derivative

        ACHTUNG: Resets previous values associated with this metric.
        """
        self._counters[metric] = True
        self._sample_store[metric] = {}

    def is_counter(self, metric):
        """Is this metric a counter?
        """
        return metric in self._counters

    def gauge(self, metric):
        """Treats the metric as a gauge, i.e. keep the data as is

        ACHTUNG: Resets previous values associated with this metric.
        """
        self._sample_store[metric] = {}

    def is_metric(self, metric):
        return metric in self._sample_store

    def is_gauge(self, metric):
        return self.is_metric(metric) and not self.is_counter(metric)

    def get_metric_names(self):
        """Get all metric names.
        """
        return self._sample_store.keys()

    def save_gauge(self, metric, value, timestamp=None,
                   dimensions=None, hostname=None, device_name=None):
        """Save a gauge value.
        """
        if not self.is_gauge(metric):
            self.gauge(metric)
        self.save_sample(metric, value, timestamp, dimensions, hostname, device_name)

    def save_sample(self, metric, value, timestamp=None,
                    dimensions=None, hostname=None, device_name=None):
        """Save a simple sample, evict old values if needed.
        """
        if timestamp is None:
            timestamp = time.time()
        if metric not in self._sample_store:
            raise exceptions.CheckException("Saving a sample for an undefined metric: %s" % metric)
        try:
            value = util.cast_metric_val(value)
        except ValueError as ve:
            raise exceptions.NaN(ve)

        # Data eviction rules
        key = (tuple(sorted(dimensions.items())), device_name)
        if self.is_gauge(metric):
            self._sample_store[metric][key] = ((timestamp, value, hostname, device_name), )
        elif self.is_counter(metric):
            if self._sample_store[metric].get(key) is None:
                self._sample_store[metric][key] = [(timestamp, value, hostname, device_name)]
            else:
                self._sample_store[metric][key] = self._sample_store[metric][key][-1:] + \
                    [(timestamp, value, hostname, device_name)]
        else:
            raise exceptions.CheckException("%s must be either gauge or counter, skipping sample at %s" %
                                                                 (metric, time.ctime(timestamp)))

        if self.is_gauge(metric):
            # store[metric][dimensions] = (ts, val) - only 1 value allowed
            assert len(self._sample_store[metric][key]) == 1, self._sample_store[metric]
        elif self.is_counter(metric):
            assert len(self._sample_store[metric][key]) in (1, 2), self._sample_store[metric]

    @classmethod
    def _rate(cls, sample1, sample2):
        """Simple rate.
        """
        try:
            rate_interval = sample2[0] - sample1[0]
            if rate_interval == 0:
                raise exceptions.Infinity()

            delta = sample2[1] - sample1[1]
            if delta < 0:
                raise exceptions.UnknownValue()

            return (sample2[0], delta / rate_interval, sample2[2], sample2[3])
        except exceptions.Infinity:
            raise
        except exceptions.UnknownValue:
            raise
        except Exception as e:
            raise exceptions.NaN(e)

    def get_sample_with_timestamp(self, metric, dimensions=None, device_name=None, expire=True):
        """Get (timestamp-epoch-style, value).
        """

        # Get the proper dimensions
        key = (tuple(sorted(dimensions.items())), device_name)

        # Never seen this metric
        if metric not in self._sample_store:
            raise exceptions.UnknownValue()

        # Not enough value to compute rate
        elif self.is_counter(metric) and len(self._sample_store[metric][key]) < 2:
            raise exceptions.UnknownValue()

        elif self.is_counter(metric) and len(self._sample_store[metric][key]) >= 2:
            res = self._rate(
                self._sample_store[metric][key][-2], self._sample_store[metric][key][-1])
            if expire:
                del self._sample_store[metric][key][:-1]
            return res

        elif self.is_gauge(metric) and len(self._sample_store[metric][key]) >= 1:
            return self._sample_store[metric][key][-1]

        else:
            raise exceptions.UnknownValue()

    def get_sample(self, metric, dimensions=None, device_name=None, expire=True):
        """Return the last value for that metric.
        """
        x = self.get_sample_with_timestamp(metric, dimensions, device_name, expire)
        assert isinstance(x, tuple) and len(x) == 4, x
        return x[1]

    def get_samples_with_timestamps(self, expire=True):
        """Return all values {metric: (ts, value)} for non-tagged metrics.
        """
        values = {}
        for m in self._sample_store:
            try:
                values[m] = self.get_sample_with_timestamp(m, expire=expire)
            except Exception:
                pass
        return values

    def get_samples(self, expire=True):
        """Return all values {metric: value} for non-tagged metrics.
        """
        values = {}
        for m in self._sample_store:
            try:
                # Discard the timestamp
                values[m] = self.get_sample_with_timestamp(m, expire=expire)[1]
            except Exception:
                pass
        return values

    def get_metrics(self, expire=True, prettyprint=False):
        """Get all metrics, including the ones that are tagged.

        This is the preferred method to retrieve metrics

        @return the list of samples
        @rtype [(metric_name, timestamp, value,
                {"dimensions": {"name1": "key1", "name2": "key2"}}), ...]
        """
        metrics = []
        for m in self._sample_store:
            try:
                for key in self._sample_store[m]:
                    dimensions_list, device_name = key
                    dimensions = dict(dimensions_list)
                    try:
                        ts, val, hostname, device_name = self.get_sample_with_timestamp(
                            m, dimensions, device_name, expire)
                    except exceptions.UnknownValue:
                        continue
                    attributes = {}
                    if dimensions_list:
                        attributes['dimensions'] = self._set_dimensions(dimensions)
                    if hostname:
                        attributes['hostname'] = hostname
                    if device_name:
                        attributes['device'] = device_name
                    metrics.append((m, int(ts), val, attributes))
            except Exception:
                pass
            if prettyprint:
                print("Metrics: {0}".format(metrics))
        return metrics


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

        self.aggregator = aggregator.MetricsAggregator(self.hostname,
                                                       recent_point_threshold=agent_config.get('recent_point_threshold',
                                                                                               None))

        self.events = []
        self.instances = instances or []
        self.warnings = []
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
        self.aggregator.gauge(metric,
                              value,
                              dimensions,
                              delegated_tenant,
                              hostname,
                              device_name,
                              timestamp,
                              value_meta)

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
        self.aggregator.increment(metric,
                                  value,
                                  dimensions,
                                  delegated_tenant,
                                  hostname,
                                  device_name,
                                  value_meta)

    def decrement(self, metric, value=-1, dimensions=None, delegated_tenant=None,
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
        self.aggregator.decrement(metric,
                                  value,
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
        self.aggregator.rate(metric,
                             value,
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
        self.aggregator.histogram(metric,
                                  value,
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
        self.aggregator.set(metric,
                            value,
                            dimensions,
                            delegated_tenant,
                            hostname,
                            device_name,
                            value_meta)

    def event(self, event):
        """Save an event.

        :param event: The event payload as a dictionary. Has the following
        structure:

            {
                "timestamp": int, the epoch timestamp for the event,
                "event_type": string, the event time name,
                "api_key": string, the api key of the account to associate the event with,
                "msg_title": string, the title of the event,
                "msg_text": string, the text body of the event,
                "alert_type": (optional) string, one of ('error', 'warning', 'success', 'info').
                    Defaults to 'info'.
                "source_type_name": (optional) string, the source type name,
                "host": (optional) string, the name of the host,
                "dimensions": (optional) a dictionary of dimensions to associate with this event
            }
        """
        if event.get('api_key') is None:
            event['api_key'] = self.agent_config['api_key']
        self.events.append(event)

    def has_events(self):
        """Check whether the check has saved any events

        @return whether or not the check has saved any events
        @rtype boolean
        """
        return len(self.events) > 0

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

    def get_events(self):
        """Return a list of the events saved by the check, if any

        @return the list of events saved by this check
        @rtype list of event dictionaries
        """
        events = self.events
        self.events = []
        return events

    def has_warnings(self):
        """Check whether the instance run created any warnings.
        """
        return len(self.warnings) > 0

    def warning(self, warning_message):
        """Add a warning message that will be printed in the info page

        :param warning_message: String. Warning message to be displayed
        """
        self.warnings.append(warning_message)

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

    def get_warnings(self):
        """Return the list of warnings messages to be displayed in the info page.
        """
        warnings = self.warnings
        self.warnings = []
        return warnings

    def run(self):
        """Run all instances.
        """
        instance_statuses = []
        for i, instance in enumerate(self.instances):
            try:
                self.check(instance)
                if self.has_warnings():
                    instance_status = check_status.InstanceStatus(i,
                                                                  check_status.STATUS_WARNING,
                                                                  warnings=self.get_warnings())
                else:
                    instance_status = check_status.InstanceStatus(i,
                                                                  check_status.STATUS_OK)
            except Exception as e:
                self.log.exception("Check '%s' instance #%s failed" % (self.name, i))
                instance_status = check_status.InstanceStatus(i,
                                                              check_status.STATUS_ERROR,
                                                              error=e,
                                                              tb=traceback.format_exc())
            instance_statuses.append(instance_status)
        return instance_statuses

    def check(self, instance):
        """Overriden by the check class. This will be called to run the check.

        :param instance: A dict with the instance information. This will vary
        depending on your config structure.
        """
        raise NotImplementedError()

    @staticmethod
    def stop():
        """To be executed when the agent is being stopped to clean ressources.
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


def run_check(name, path=None):
    import tests.common

    # Read the config file
    config = Config()
    confd_path = path or os.path.join(config.get_confd_path(),
                                      '{0}.yaml'.format(name))

    try:
        f = open(confd_path)
    except IOError:
        raise Exception('Unable to open configuration at %s' % confd_path)

    config_str = f.read()
    f.close()

    # Run the check
    check, instances = tests.common.get_check(name, config_str)
    if not instances:
        raise Exception('YAML configuration returned no instances.')
    for instance in instances:
        check.check(instance)
        if check.has_events():
            print("Events:\n")
            pprint.pprint(check.get_events(), indent=4)
        print("Metrics:\n")
        pprint.pprint(check.get_metrics(), indent=4)
