""" Aggregation classes used by the collector and statsd to batch messages sent to the forwarder.
"""
import logging
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


class MetricsAggregator(object):

    """
    A metric aggregator class.
    """

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
        self.metric_type_to_class = {
            'g': metrics_pkg.Gauge,
            'c': metrics_pkg.Counter,
            'h': metrics_pkg.Histogram,
            'ms': metrics_pkg.Histogram,
            's': metrics_pkg.Set,
            'r': metrics_pkg.Rate,
        }

    def decrement(self, name, value=-1, dimensions=None, delegated_tenant=None,
                  hostname=None, device_name=None, value_meta=None):
        self.submit_metric(name, value, 'c', dimensions, delegated_tenant,
                           hostname, device_name, value_meta)

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
        event = {
            'msg_title': title,
            'msg_text': text,
            }
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
            except Exception as e:
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

    @staticmethod
    def formatter(metric, value, timestamp, dimensions, hostname, delegated_tenant=None,
                  device_name=None, metric_type=None, value_meta=None):
        """ Formats metrics, put them into a Measurement class
            (metric, timestamp, value, {"dimensions": {"name1": "value1", "name2": "value2"}, ...})
            dimensions should be a dictionary
        """
        if hostname:
            dimensions.update({'hostname': hostname})
        if device_name:
            dimensions.update({'device': device_name})

        return metrics_pkg.Measurement(metric,
                                       int(timestamp),
                                       value,
                                       dimensions,
                                       delegated_tenant=delegated_tenant,
                                       value_meta=value_meta)

    def gauge(self, name, value, dimensions=None, delegated_tenant=None,
              hostname=None, device_name=None, timestamp=None, value_meta=None):
        self.submit_metric(name, value, 'g', dimensions, delegated_tenant,
                           hostname, device_name, value_meta, timestamp)

    def histogram(self, name, value, dimensions=None, delegated_tenant=None,
                  hostname=None, device_name=None, value_meta=None):
        self.submit_metric(name, value, 'h', dimensions, delegated_tenant,
                           hostname, device_name, value_meta)

    def increment(self, name, value=1, dimensions=None, delegated_tenant=None,
                  hostname=None, device_name=None, value_meta=None):
        self.submit_metric(name, value, 'c', dimensions, delegated_tenant,
                           hostname, device_name, value_meta)

    def packets_per_second(self, interval):
        if interval == 0:
            return 0
        return round(float(self.count) / interval, 2)

    def rate(self, name, value, dimensions=None, delegated_tenant=None,
             hostname=None, device_name=None, value_meta=None):
        self.submit_metric(name, value, 'r', dimensions, delegated_tenant,
                           hostname, device_name, value_meta)

    def set(self, name, value, dimensions=None, delegated_tenant=None,
            hostname=None, device_name=None, value_meta=None):
        self.submit_metric(name, value, 's', dimensions, delegated_tenant,
                           hostname, device_name, value_meta)

    def submit_metric(self, name, value, mtype, dimensions=None,
                      delegated_tenant=None, hostname=None, device_name=None,
                      value_meta=None, timestamp=None, sample_rate=1):

        if value_meta:
            meta = tuple(value_meta.items())
        else:
            meta = None

        context = (name, tuple(dimensions.items()), meta, delegated_tenant,
                   hostname, device_name)

        if context not in self.metrics:
            metric_class = self.metric_type_to_class[mtype]
            self.metrics[context] = metric_class(self.formatter,
                                                 name,
                                                 dimensions,
                                                 hostname or self.hostname,
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
