# (C) Copyright 2015-2017 Hewlett Packard Enterprise Development LP
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

""" Aggregation classes used by the collector and statsd to batch messages sent to the forwarder.
"""
import json
import logging
from time import time

import monasca_common.validation.metrics as metric_validator

log = logging.getLogger(__name__)

# This is used to ensure that metrics with a timestamp older than
# RECENT_POINT_THRESHOLD_DEFAULT seconds (or the value passed in to
# the MetricsAggregator constructor) get discarded rather than being
# input into the incorrect bucket. Currently, the MetricsAggregator
# does not support submitting values for the past, and all values get
# submitted for the timestamp passed into the flush() function.
RECENT_POINT_THRESHOLD_DEFAULT = 3600
VALUE_META_VALUE_MAX_LENGTH = 2048


class MetricsAggregator(object):
    """A metric aggregator class."""

    def __init__(self, hostname, recent_point_threshold=None, tenant_id=None):
        self.total_count = 0
        self.count = 0
        self.hostname = hostname
        self.global_delegated_tenant = tenant_id

        recent_point_threshold = recent_point_threshold or RECENT_POINT_THRESHOLD_DEFAULT
        self.recent_point_threshold = int(recent_point_threshold)
        self.num_discarded_old_points = 0

        self.metrics = {}

    def flush(self):
        # Flush samples.  The individual metrics reset their internal samples
        # when required
        metrics = []
        for context, metric in self.metrics.items():
            try:
                metrics.extend(metric.flush())
            except Exception:
                log.exception('Error flushing {0} metrics.'.format(metric.metric['name']))

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

    def get_hostname_to_post(self, hostname):
        if 'SUPPRESS' == hostname:
            return None
        return hostname or self.hostname

    def packets_per_second(self, interval):
        if interval == 0:
            return 0
        return round(float(self.count) / interval, 2)

    def submit_metric(self, name, value, metric_class, dimensions=None,
                      delegated_tenant=None, hostname=None, device_name=None,
                      value_meta=None, timestamp=None, sample_rate=1):
        # validate dimensions, name, value and value meta
        if dimensions:
            metric_validator.validate_dimensions(dimensions)

        metric_validator.validate_name(name)

        metric_validator.validate_value(value)

        if value_meta:
            metric_validator.validate_value_meta(value_meta)

        hostname_to_post = self.get_hostname_to_post(hostname)

        tenant_to_post = delegated_tenant or self.global_delegated_tenant

        dimensions_copy = dimensions.copy()

        if 'hostname' not in dimensions_copy and hostname_to_post:
            dimensions_copy.update({'hostname': hostname_to_post})

        # TODO(joe): Shouldn't device_name be added to dimensions in the check
        #            plugin?  Why is it special cased through so many layers?
        if device_name:
            dimensions_copy.update({'device': device_name})

        # TODO(joe): Decide if hostname_to_post and device_name are necessary
        #            for the context tuple
        context = (name, tuple(dimensions_copy.items()), tenant_to_post,
                   hostname_to_post, device_name)

        if context not in self.metrics:
            self.metrics[context] = metric_class(name,
                                                 dimensions_copy,
                                                 tenant=tenant_to_post)
        cur_time = time()
        if timestamp is not None:
            if cur_time - int(timestamp) > self.recent_point_threshold:
                log.debug(
                    "Discarding {0} - ts = {1}, current ts = {2} ".format(name,
                                                                          timestamp,
                                                                          cur_time))
                self.num_discarded_old_points += 1
                return
        else:
            timestamp = cur_time
        self.metrics[context].value_meta = value_meta
        self.metrics[context].sample(value, sample_rate, timestamp)


def get_value_meta_overage(value_meta):
    if len(json.dumps(value_meta)) > VALUE_META_VALUE_MAX_LENGTH:
        return len(json.dumps(value_meta)) - VALUE_META_VALUE_MAX_LENGTH
    return 0
