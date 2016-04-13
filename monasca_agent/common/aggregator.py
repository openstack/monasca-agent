# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP
""" Aggregation classes used by the collector and statsd to batch messages sent to the forwarder.
"""
import json
import logging
import re
from time import time

import monasca_agent.common.metrics as metrics_pkg


log = logging.getLogger(__name__)

# This is used to ensure that metrics with a timestamp older than
# RECENT_POINT_THRESHOLD_DEFAULT seconds (or the value passed in to
# the MetricsAggregator constructor) get discarded rather than being
# input into the incorrect bucket. Currently, the MetricsAggregator
# does not support submitting values for the past, and all values get
# submitted for the timestamp passed into the flush() function.
RECENT_POINT_THRESHOLD_DEFAULT = 3600
VALUE_META_MAX_NUMBER = 16
VALUE_META_VALUE_MAX_LENGTH = 2048
VALUE_META_NAME_MAX_LENGTH = 255

invalid_chars = "<>={}(),\"\\\\;&"
restricted_dimension_chars = re.compile('[' + invalid_chars + ']')
restricted_name_chars = re.compile('[' + invalid_chars + ' ' + ']')


class InvalidMetricName(Exception):
    pass


class InvalidDimensionKey(Exception):
    pass


class InvalidDimensionValue(Exception):
    pass


class InvalidValue(Exception):
    pass


class InvalidValueMeta(Exception):
    pass


class MetricsAggregator(object):
    """A metric aggregator class."""

    def __init__(self, hostname, recent_point_threshold=None):
        self.events = []
        self.total_count = 0
        self.count = 0
        self.event_count = 0
        self.hostname = hostname

        recent_point_threshold = recent_point_threshold or RECENT_POINT_THRESHOLD_DEFAULT
        self.recent_point_threshold = int(recent_point_threshold)
        self.num_discarded_old_points = 0

        self.metrics = {}

    def event(
            self,
            title,
            text,
            date_happened=None,
            alert_type=None,
            aggregation_key=None,
            source_type_name=None,
            priority=None,
            dimensions=None,
            hostname=None):
        event = {'msg_title': title,
                 'msg_text': text}
        if date_happened is not None:
            event['timestamp'] = date_happened
        else:
            event['timestamp'] = int(time())
        if alert_type is not None:
            event['alert_type'] = alert_type
        if aggregation_key is not None:
            event['aggregation_key'] = aggregation_key
        if source_type_name is not None:
            event['source_type_name'] = source_type_name
        if priority is not None:
            event['priority'] = priority
        if dimensions is not None:
            event['dimensions'] = dimensions
        if hostname is not None:
            event['host'] = hostname
        else:
            event['host'] = self.hostname

        self.events.append(event)

    def flush(self):
        timestamp = time()

        # Flush samples.  The individual metrics reset their internal samples
        # when required
        metrics = []
        for context, metric in self.metrics.items():
            try:
                metrics.extend(metric.flush(timestamp))
            except Exception:
                log.exception('Error flushing {0} metrics.'.format(metric.name))

        # Log a warning regarding metrics with old timestamps being submitted
        if self.num_discarded_old_points > 0:
            log.warn('{0} points were discarded as a result of having an old timestamp'.format(
                     self.num_discarded_old_points))
            self.num_discarded_old_points = 0

        # Save some stats.
        log.debug("received {0} payloads since last flush".format(self.count))
        self.total_count += self.count
        self.count = 0
        return metrics

    def flush_events(self):
        events = self.events
        self.events = []

        self.total_count += self.event_count
        self.event_count = 0

        log.debug("Received {0} events since last flush".format(len(events)))

        return events

    def get_hostname_to_post(self, hostname):
        if 'SUPPRESS' == hostname:
            return None
        return hostname or self.hostname

    @staticmethod
    def formatter(metric, value, timestamp, dimensions, hostname, delegated_tenant=None,
                  device_name=None, metric_type=None, value_meta=None):
        """Formats metrics, put them into a Measurement class
           (metric, timestamp, value, {"dimensions": {"name1": "value1", "name2": "value2"}, ...})
           dimensions should be a dictionary
        """
        if 'hostname' not in dimensions and hostname:
            dimensions.update({'hostname': hostname})
        if device_name:
            dimensions.update({'device': device_name})

        return metrics_pkg.Measurement(metric,
                                       int(timestamp),
                                       value,
                                       dimensions,
                                       delegated_tenant=delegated_tenant,
                                       value_meta=value_meta)

    def packets_per_second(self, interval):
        if interval == 0:
            return 0
        return round(float(self.count) / interval, 2)

    def _valid_value_meta(self, value_meta, name, dimensions):
        if len(value_meta) > VALUE_META_MAX_NUMBER:
            msg = "Too many valueMeta entries {0}, limit is {1}: {2} -> {3} valueMeta {4}"
            log.error(msg.format(len(value_meta), VALUE_META_MAX_NUMBER, name, dimensions, value_meta))
            return False
        for key, value in value_meta.iteritems():
            if not key:
                log.error("valueMeta name cannot be empty: {0} -> {1}".format(name, dimensions))
                return False
            if len(key) > VALUE_META_NAME_MAX_LENGTH:
                msg = "valueMeta name {0} must be {1} characters or less: {2} -> {3}"
                log.error(msg.format(key, VALUE_META_NAME_MAX_LENGTH, name, dimensions))
                return False

        try:
            value_meta_json = json.dumps(value_meta)
            if len(value_meta_json) > VALUE_META_VALUE_MAX_LENGTH:
                msg = "valueMeta name value combinations must be {0} characters or less: {1} -> {2} valueMeta {3}"
                log.error(msg.format(VALUE_META_VALUE_MAX_LENGTH, name, dimensions, value_meta))
                return False
        except Exception:
                log.error("Unable to serialize valueMeta into JSON: {2} -> {3}".format(name, dimensions))
                return False

        return True

    def submit_metric(self, name, value, metric_class, dimensions=None,
                      delegated_tenant=None, hostname=None, device_name=None,
                      value_meta=None, timestamp=None, sample_rate=1):
        if dimensions:
            for k, v in dimensions.iteritems():
                if not isinstance(k, (str, unicode)):
                    log.error("invalid dimension key {0} must be a string: {1} -> {2}".format(k, name, dimensions))
                    raise InvalidDimensionKey
                if len(k) > 255 or len(k) < 1:
                    log.error("invalid length for dimension key {0}: {1} -> {2}".format(k, name, dimensions))
                    raise InvalidDimensionKey
                if restricted_dimension_chars.search(k) or re.match('^_', k):
                    log.error("invalid characters in dimension key {0}: {1} -> {2}".format(k, name, dimensions))
                    raise InvalidDimensionKey

                if not isinstance(v, (str, unicode)):
                    log.error("invalid dimension value {0} for key {1} must be a string: {2} -> {3}".format(v, k, name,
                                                                                                            dimensions))
                    raise InvalidDimensionValue
                if len(v) > 255 or len(v) < 1:
                    log.error("invalid length dimension value {0} for key {1}: {2} -> {3}".format(v, k, name,
                                                                                                  dimensions))
                    raise InvalidDimensionValue
                if restricted_dimension_chars.search(v):
                    log.error("invalid characters in dimension value {0} for key {1}: {2} -> {3}".format(v, k, name,
                                                                                                         dimensions))
                    raise InvalidDimensionValue

        if not isinstance(name, (str, unicode)):
            log.error("invalid metric name must be a string: {0} -> {1}".format(name, dimensions))
            raise InvalidMetricName
        if len(name) > 255 or len(name) < 1:
            log.error("invalid length for metric name: {0} -> {1}".format(name, dimensions))
            raise InvalidMetricName
        if restricted_name_chars.search(name):
            log.error("invalid characters in metric name: {0} -> {1}".format(name, dimensions))
            raise InvalidMetricName

        if not isinstance(value, (int, long, float)):
            log.error("invalid value {0} is not of number type for metric {1}".format(value, name))
            raise InvalidValue

        if value_meta:
            if not self._valid_value_meta(value_meta, name, dimensions):
                raise InvalidValueMeta
            meta = tuple(value_meta.items())
        else:
            meta = None

        hostname_to_post = self.get_hostname_to_post(hostname)
        context = (name, tuple(dimensions.items()), meta, delegated_tenant,
                   hostname_to_post, device_name)

        if context not in self.metrics:
            self.metrics[context] = metric_class(self.formatter,
                                                 name,
                                                 dimensions,
                                                 hostname_to_post,
                                                 device_name,
                                                 delegated_tenant,
                                                 value_meta)
        cur_time = time()
        if timestamp is not None:
            if cur_time - int(timestamp) > self.recent_point_threshold:
                log.debug("Discarding {0} - ts = {1}, current ts = {2} ".format(name, timestamp, cur_time))
                self.num_discarded_old_points += 1
                return
        else:
            timestamp = cur_time
        self.metrics[context].sample(value, sample_rate, timestamp)
