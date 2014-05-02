""" Aggregation classes used by the collector and dogstatsd to batch messages sent to the forwarder.
"""
import logging
from time import time

from metrics import MetricTypes
from monagent.common.metrics import Gauge, BucketGauge, Counter, Histogram, Set, Rate


log = logging.getLogger(__name__)


# This is used to ensure that metrics with a timestamp older than
# RECENT_POINT_THRESHOLD_DEFAULT seconds (or the value passed in to
# the MetricsAggregator constructor) get discarded rather than being
# input into the incorrect bucket. Currently, the MetricsAggregator
# does not support submitting values for the past, and all values get
# submitted for the timestamp passed into the flush() function.
# The MetricsBucketAggregator uses times that are aligned to "buckets"
# that are the length of the interval that is passed into the
# MetricsBucketAggregator constructor.
RECENT_POINT_THRESHOLD_DEFAULT = 3600


class Infinity(Exception):
    pass


class UnknownValue(Exception):
    pass


class Aggregator(object):
    """
    Abstract metric aggregator class.
    """
    # Types of metrics that allow strings
    ALLOW_STRINGS = ['s', ]

    def __init__(self, hostname, interval=1.0, expiry_seconds=300, recent_point_threshold=None):
        self.events = []
        self.total_count = 0
        self.count = 0
        self.event_count = 0
        self.hostname = hostname
        self.expiry_seconds = expiry_seconds
        self.interval = float(interval)

        recent_point_threshold = recent_point_threshold or RECENT_POINT_THRESHOLD_DEFAULT
        self.recent_point_threshold = int(recent_point_threshold)
        self.num_discarded_old_points = 0

    @staticmethod
    def formatter(metric, value, timestamp, dimensions, hostname, device_name=None, metric_type=None, interval=None):
        """ Formats metrics. Will look like:
            (metric, timestamp, value, {"dimensions": {"name1": "value1", "name2": "value2"}, ...})
            dimensions should be a dictionary
        """
        #todo is there a clearer way to do this, pass in a dictionary in the first place for attributes?
        attributes = {}
        if dimensions:
            attributes['dimensions'] = dimensions
        if hostname:
            attributes['hostname'] = hostname
        if device_name:
            attributes['device_name'] = device_name
        if metric_type:
            attributes['type'] = metric_type
        if interval:
            attributes['interval'] = interval

        if attributes:
            return (metric, int(timestamp), value, attributes)
        return (metric, int(timestamp), value)

    def packets_per_second(self, interval):
        if interval == 0:
            return 0
        return round(float(self.count)/interval, 2)

    def parse_metric_packet(self, packet):
        name_and_metadata = packet.split(':', 1)

        if len(name_and_metadata) != 2:
            raise Exception('Unparseable metric packet: %s' % packet)

        name = name_and_metadata[0]
        metadata = name_and_metadata[1].split('|')

        if len(metadata) < 2:
            raise Exception('Unparseable metric packet: %s' % packet)

        # Submit the metric
        raw_value = metadata[0]
        metric_type = metadata[1]

        if metric_type in self.ALLOW_STRINGS:
            value = raw_value
        else:
            # Try to cast as an int first to avoid precision issues, then as a
            # float.
            try:
                value = int(raw_value)
            except ValueError:
                try:
                    value = float(raw_value)
                except ValueError:
                    # Otherwise, raise an error saying it must be a number
                    raise Exception('Metric value must be a number: %s, %s' % (name, raw_value))


        # Parse the optional values - sample rate & dimensions.
        sample_rate = 1
        dimensions = None
        for m in metadata[2:]:
            # Parse the sample rate
            if m[0] == '@':
                sample_rate = float(m[1:])
                assert 0 <= sample_rate <= 1
            elif m[0] == '#':
                dim_list = [dim.split(':') for dim in m[1:].split(',')]
                dimensions = {key.strip(): value.strip() for key, value in dim_list}

        return name, value, metric_type, dimensions, sample_rate

    @staticmethod
    def _unescape_event_text(string):
        return string.replace('\\n', '\n')

    def parse_event_packet(self, packet):
        try:
            name_and_metadata = packet.split(':', 1)
            if len(name_and_metadata) != 2:
                raise Exception(u'Unparseable event packet: %s' % packet)
            # Event syntax:
            # _e{5,4}:title|body|meta
            name = name_and_metadata[0]
            metadata = unicode(name_and_metadata[1])
            title_length, text_length = name.split(',')
            title_length = int(title_length[3:])
            text_length = int(text_length[:-1])

            event = {
                'title': metadata[:title_length],
                'text': self._unescape_event_text(metadata[title_length+1:title_length+text_length+1])
            }
            meta = metadata[title_length+text_length+1:]
            for m in meta.split('|')[1:]:
                if m[0] == u't':
                    event['alert_type'] = m[2:]
                elif m[0] == u'k':
                    event['aggregation_key'] = m[2:]
                elif m[0] == u's':
                    event['source_type_name'] = m[2:]
                elif m[0] == u'd':
                    event['date_happened'] = int(m[2:])
                elif m[0] == u'p':
                    event['priority'] = m[2:]
                elif m[0] == u'h':
                    event['hostname'] = m[2:]
                elif m[0] == u'#':
                    event['dimensions'] = sorted(m[1:].split(u','))
            return event
        except IndexError, ValueError:
            raise Exception(u'Unparseable event packet: %s' % packet)

    def submit_packets(self, packets):
        for packet in packets.split("\n"):

            if not packet.strip():
                continue

            if packet.startswith('_e'):
                self.event_count += 1
                event = self.parse_event_packet(packet)
                self.event(**event)
            else:
                self.count += 1
                name, value, mtype, dimensions, sample_rate = self.parse_metric_packet(packet)
                self.submit_metric(name, value, mtype, dimensions=dimensions, sample_rate=sample_rate)

    def submit_metric(self, name, value, mtype, dimensions=None, hostname=None,
                                device_name=None, timestamp=None, sample_rate=1):
        """ Add a metric to be aggregated """
        raise NotImplementedError()

    def event(self, title, text, date_happened=None, alert_type=None, aggregation_key=None, source_type_name=None, priority=None, dimensions=None, hostname=None):
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
        """ Flush aggreaged metrics """
        raise NotImplementedError()

    def flush_events(self):
        events = self.events
        self.events = []

        self.total_count += self.event_count
        self.event_count = 0

        log.debug("Received %d events since last flush" % len(events))

        return events

    def send_packet_count(self, metric_name):
        self.submit_metric(metric_name, self.count, 'g')


class MetricsBucketAggregator(Aggregator):
    """
    A metric aggregator class.
    """

    def __init__(self, hostname, interval=1.0, expiry_seconds=300, recent_point_threshold=None):
        super(MetricsBucketAggregator, self).__init__(hostname, interval, expiry_seconds, recent_point_threshold)
        self.metric_by_bucket = {}
        self.last_sample_time_by_context = {}
        self.current_bucket = None
        self.current_mbc = None
        self.last_flush_cutoff_time = 0
        self.metric_type_to_class = {
            'g': BucketGauge,
            'c': Counter,
            'h': Histogram,
            'ms': Histogram,
            's': Set,
        }

    def calculate_bucket_start(self, timestamp):
        return timestamp - (timestamp % self.interval)

    def submit_metric(self, name, value, mtype, dimensions=None, hostname=None,
                                device_name=None, timestamp=None, sample_rate=1):
        # Avoid calling extra functions to dedupe dimensions if there are none
        # Note: if you change the way that context is created, please also change create_empty_metrics,
        #  which counts on this order
        if dimensions is None:
            context = (name, {}, hostname, device_name)
        else:
            context = (name, dimensions, hostname, device_name)

        cur_time = time()
        # Check to make sure that the timestamp that is passed in (if any) is not older than
        #  recent_point_threshold.  If so, discard the point.
        if timestamp is not None and cur_time - int(timestamp) > self.recent_point_threshold:
            log.debug("Discarding %s - ts = %s , current ts = %s " % (name, timestamp, cur_time))
            self.num_discarded_old_points += 1
        else:
            timestamp = timestamp or cur_time
            # Keep track of the buckets using the timestamp at the start time of the bucket
            bucket_start_timestamp = self.calculate_bucket_start(timestamp)
            if bucket_start_timestamp == self.current_bucket:
                metric_by_context = self.current_mbc
            else:
                if bucket_start_timestamp not in self.metric_by_bucket:
                    self.metric_by_bucket[bucket_start_timestamp] = {}
                metric_by_context = self.metric_by_bucket[bucket_start_timestamp]
                self.current_bucket = bucket_start_timestamp
                self.current_mbc = metric_by_context

            if context not in metric_by_context:
                metric_class = self.metric_type_to_class[mtype]
                metric_by_context[context] = metric_class(self.formatter, name, dimensions,
                    hostname or self.hostname, device_name)

            metric_by_context[context].sample(value, sample_rate, timestamp)

    def create_empty_metrics(self, sample_time_by_context, expiry_timestamp, flush_timestamp, metrics):
        # Even if no data is submitted, Counters keep reporting "0" for expiry_seconds.  The other Metrics
        #  (Set, Gauge, Histogram) do not report if no data is submitted
        for context, last_sample_time in sample_time_by_context.items():
            if last_sample_time < expiry_timestamp:
                log.debug("%s hasn't been submitted in %ss. Expiring." % (context, self.expiry_seconds))
                self.last_sample_time_by_context.pop(context, None)
            else:
                # The expiration currently only applies to Counters
                # This counts on the ordering of the context created in submit_metric not changing
                metric = Counter(self.formatter, context[0], context[1], context[2], context[3])
                metrics += metric.flush(flush_timestamp, self.interval)

    def flush(self):
        cur_time = time()
        flush_cutoff_time = self.calculate_bucket_start(cur_time)
        expiry_timestamp = cur_time - self.expiry_seconds

        metrics = []

        if self.metric_by_bucket:
            # We want to process these in order so that we can check for and expired metrics and
            #  re-create non-expired metrics.  We also mutate self.metric_by_bucket.
            for bucket_start_timestamp in sorted(self.metric_by_bucket.keys()):
                metric_by_context = self.metric_by_bucket[bucket_start_timestamp]
                if bucket_start_timestamp < flush_cutoff_time:
                    not_sampled_in_this_bucket = self.last_sample_time_by_context.copy()
                    # We mutate this dictionary while iterating so don't use an iterator.
                    for context, metric in metric_by_context.items():
                        if metric.last_sample_time < expiry_timestamp:
                            # This should never happen
                            log.warning("%s hasn't been submitted in %ss. Expiring." % (context, self.expiry_seconds))
                            not_sampled_in_this_bucket.pop(context, None)
                            self.last_sample_time_by_context.pop(context, None)
                        else:
                            metrics += metric.flush(bucket_start_timestamp, self.interval)
                            if isinstance(metric, Counter):
                                self.last_sample_time_by_context[context] = metric.last_sample_time
                                not_sampled_in_this_bucket.pop(context, None)
                    # We need to account for Metrics that have not expired and were not flushed for this bucket
                    self.create_empty_metrics(not_sampled_in_this_bucket, expiry_timestamp, bucket_start_timestamp, metrics)

                    del self.metric_by_bucket[bucket_start_timestamp]
        else:
            # Even if there are no metrics in this flush, there may be some non-expired counters
            #  We should only create these non-expired metrics if we've passed an interval since the last flush
            if flush_cutoff_time >= self.last_flush_cutoff_time + self.interval:
                self.create_empty_metrics(self.last_sample_time_by_context.copy(), expiry_timestamp, \
                                                flush_cutoff_time-self.interval, metrics)

        # Log a warning regarding metrics with old timestamps being submitted
        if self.num_discarded_old_points > 0:
            log.warn('%s points were discarded as a result of having an old timestamp' % self.num_discarded_old_points)
            self.num_discarded_old_points = 0

        # Save some stats.
        log.debug("received %s payloads since last flush" % self.count)
        self.total_count += self.count
        self.count = 0
        self.current_bucket = None
        self.current_mbc = None
        self.last_flush_cutoff_time = flush_cutoff_time
        return metrics


class MetricsAggregator(Aggregator):
    """
    A metric aggregator class.
    """

    def __init__(self, hostname, interval=1.0, expiry_seconds=300, recent_point_threshold=None):
        super(MetricsAggregator, self).__init__(hostname, interval, expiry_seconds, recent_point_threshold)
        self.metrics = {}
        self.metric_type_to_class = {
            'g': Gauge,
            'c': Counter,
            'h': Histogram,
            'ms': Histogram,
            's': Set,
            '_dd-r': Rate,
        }

    def submit_metric(self, name, value, mtype, dimensions=None, hostname=None,
                                device_name=None, timestamp=None, sample_rate=1):
        # Avoid calling extra functions to dedupe dimensions if there are none
        if dimensions is None:
            context = (name, {}, hostname, device_name)
        else:
            context = (name, dimensions, hostname, device_name)
        if context not in self.metrics:
            metric_class = self.metric_type_to_class[mtype]
            self.metrics[context] = metric_class(self.formatter, name, dimensions,
                hostname or self.hostname, device_name)
        cur_time = time()
        if timestamp is not None and cur_time - int(timestamp) > self.recent_point_threshold:
            log.debug("Discarding %s - ts = %s , current ts = %s " % (name, timestamp, cur_time))
            self.num_discarded_old_points += 1
        else:
            self.metrics[context].sample(value, sample_rate, timestamp)

    def gauge(self, name, value, dimensions=None, hostname=None, device_name=None, timestamp=None):
        self.submit_metric(name, value, 'g', dimensions, hostname, device_name, timestamp)

    def increment(self, name, value=1, dimensions=None, hostname=None, device_name=None):
        self.submit_metric(name, value, 'c', dimensions, hostname, device_name)

    def decrement(self, name, value=-1, dimensions=None, hostname=None, device_name=None):
        self.submit_metric(name, value, 'c', dimensions, hostname, device_name)

    def rate(self, name, value, dimensions=None, hostname=None, device_name=None):
        self.submit_metric(name, value, '_dd-r', dimensions, hostname, device_name)

    def histogram(self, name, value, dimensions=None, hostname=None, device_name=None):
        self.submit_metric(name, value, 'h', dimensions, hostname, device_name)

    def set(self, name, value, dimensions=None, hostname=None, device_name=None):
        self.submit_metric(name, value, 's', dimensions, hostname, device_name)

    def flush(self):
        timestamp = time()
        expiry_timestamp = timestamp - self.expiry_seconds

        # Flush points and remove expired metrics. We mutate this dictionary
        # while iterating so don't use an iterator.
        metrics = []
        for context, metric in self.metrics.items():
            if metric.last_sample_time < expiry_timestamp:
                log.debug("%s hasn't been submitted in %ss. Expiring." % (context, self.expiry_seconds))
                del self.metrics[context]
            else:
                metrics += metric.flush(timestamp, self.interval)

        # Log a warning regarding metrics with old timestamps being submitted
        if self.num_discarded_old_points > 0:
            log.warn('%s points were discarded as a result of having an old timestamp' % self.num_discarded_old_points)
            self.num_discarded_old_points = 0

        # Save some stats.
        log.debug("received %s payloads since last flush" % self.count)
        self.total_count += self.count
        self.count = 0
        return metrics

