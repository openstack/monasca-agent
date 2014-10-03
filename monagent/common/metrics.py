""" Metric data types
"""
from collections import namedtuple
import logging
from time import time

from monagent.common.exceptions import Infinity, UnknownValue


log = logging.getLogger(__name__)


# todo it would be best to implement a Measurement group/list container, it could then have methods for converting to json
# in the current setup both the emitter and the mon api are converting to json in for loops
# A Measurement is the standard format used to pass data from the
# collector and monstatsd to the forwarder
Measurement = namedtuple('Measurement', ['name', 'timestamp', 'value',
                                         'dimensions', 'delegated_tenant'])


class MetricTypes(object):
    GAUGE = 'gauge'
    COUNTER = 'counter'
    RATE = 'rate'


class Metric(object):

    """
    A base metric class that accepts points, slices them into time intervals
    and performs roll-ups within those intervals.
    """

    def sample(self, value, sample_rate, timestamp=None):
        """ Add a point to the given metric. """
        raise NotImplementedError()

    def flush(self, timestamp, interval):
        """ Flush all metrics up to the given timestamp. """
        raise NotImplementedError()


class Gauge(Metric):

    """ A metric that tracks a value at particular points in time. """

    def __init__(self, formatter, name, dimensions, delegated_tenant,
                 hostname, device_name):
        self.formatter = formatter
        self.name = name
        self.value = None
        self.dimensions = dimensions
        self.delegated_tenant = delegated_tenant
        self.hostname = hostname
        self.device_name = device_name
        self.last_sample_time = None
        self.timestamp = time()

    def sample(self, value, sample_rate, timestamp=None):
        self.value = value
        self.last_sample_time = time()
        self.timestamp = timestamp

    def flush(self, timestamp, interval):
        if self.value is not None:
            res = [self.formatter(
                metric=self.name,
                timestamp=self.timestamp or timestamp,
                value=self.value,
                dimensions=self.dimensions,
                delegated_tenant=self.delegated_tenant,
                hostname=self.hostname,
                device_name=self.device_name,
                metric_type=MetricTypes.GAUGE,
                interval=interval,
            )]
            self.value = None
            return res

        return []


class BucketGauge(Gauge):

    """ A metric that tracks a value at particular points in time.
    The difference beween this class and Gauge is that this class will
    report that gauge sample time as the time that Metric is flushed, as
    opposed to the time that the sample was collected.

    """

    def flush(self, timestamp, interval):
        if self.value is not None:
            res = [self.formatter(
                metric=self.name,
                timestamp=timestamp,
                value=self.value,
                dimensions=self.dimensions,
                delegated_tenant=self.delegated_tenant,
                hostname=self.hostname,
                device_name=self.device_name,
                metric_type=MetricTypes.GAUGE,
                interval=interval,
            )]
            self.value = None
            return res

        return []


class Counter(Metric):

    """ A metric that tracks a counter value. """

    def __init__(self, formatter, name, dimensions, delegated_tenant,
                 hostname, device_name):
        self.formatter = formatter
        self.name = name
        self.value = 0
        self.dimensions = dimensions
        self.delegated_tenant = delegated_tenant
        self.hostname = hostname
        self.device_name = device_name
        self.last_sample_time = None

    def sample(self, value, sample_rate, timestamp=None):
        self.value += value * int(1 / sample_rate)
        self.last_sample_time = time()

    def flush(self, timestamp, interval):
        try:
            value = self.value / interval
            return [self.formatter(
                metric=self.name,
                value=value,
                timestamp=timestamp,
                dimensions=self.dimensions,
                delegated_tenant=self.delegated_tenant,
                hostname=self.hostname,
                device_name=self.device_name,
                metric_type=MetricTypes.RATE,
                interval=interval,
            )]
        finally:
            self.value = 0


class Histogram(Metric):

    """ A metric to track the distribution of a set of values. """

    def __init__(self, formatter, name, dimensions, delegated_tenant,
                 hostname, device_name):
        self.formatter = formatter
        self.name = name
        self.count = 0
        self.samples = []
        self.percentiles = [0.95]
        self.dimensions = dimensions
        self.delegated_tenant = delegated_tenant
        self.hostname = hostname
        self.device_name = device_name
        self.last_sample_time = None

    def sample(self, value, sample_rate, timestamp=None):
        self.count += int(1 / sample_rate)
        self.samples.append(value)
        self.last_sample_time = time()

    def flush(self, ts, interval):
        if not self.count:
            return []

        self.samples.sort()
        length = len(self.samples)

        max_ = self.samples[-1]
        med = self.samples[int(round(length / 2 - 1))]
        avg = sum(self.samples) / float(length)

        metric_aggrs = [
            ('max', max_, MetricTypes.GAUGE),
            ('median', med, MetricTypes.GAUGE),
            ('avg', avg, MetricTypes.GAUGE),
            ('count', self.count / interval, MetricTypes.RATE)
        ]

        metrics = [self.formatter(
            hostname=self.hostname,
            device_name=self.device_name,
            dimensions=self.dimensions,
            delegated_tenant=self.delegated_tenant,
            metric='%s.%s' % (self.name, suffix),
            value=value,
            timestamp=ts,
            metric_type=metric_type,
            interval=interval,
        ) for suffix, value, metric_type in metric_aggrs
        ]

        for p in self.percentiles:
            val = self.samples[int(round(p * length - 1))]
            name = '%s.%spercentile' % (self.name, int(p * 100))
            metrics.append(self.formatter(
                hostname=self.hostname,
                dimensions=self.dimensions,
                delegated_tenant=self.delegated_tenant,
                metric=name,
                value=val,
                timestamp=ts,
                metric_type=MetricTypes.GAUGE,
                interval=interval,
            ))

        # Reset our state.
        self.samples = []
        self.count = 0

        return metrics


class Set(Metric):

    """ A metric to track the number of unique elements in a set. """

    def __init__(self, formatter, name, dimensions, delegated_tenant,
                 hostname, device_name):
        self.formatter = formatter
        self.name = name
        self.dimensions = dimensions
        self.delegated_tenant = delegated_tenant
        self.hostname = hostname
        self.device_name = device_name
        self.values = set()
        self.last_sample_time = None

    def sample(self, value, sample_rate, timestamp=None):
        self.values.add(value)
        self.last_sample_time = time()

    def flush(self, timestamp, interval):
        if not self.values:
            return []
        try:
            return [self.formatter(
                hostname=self.hostname,
                device_name=self.device_name,
                dimensions=self.dimensions,
                delegated_tenant=self.delegated_tenant,
                metric=self.name,
                value=len(self.values),
                timestamp=timestamp,
                metric_type=MetricTypes.GAUGE,
                interval=interval,
            )]
        finally:
            self.values = set()


class Rate(Metric):

    """ Track the rate of metrics over each flush interval """

    def __init__(self, formatter, name, dimensions, delegated_tenant,
                 hostname, device_name):
        self.formatter = formatter
        self.name = name
        self.dimensions = dimensions
        self.delegated_tenant = delegated_tenant
        self.hostname = hostname
        self.device_name = device_name
        self.samples = []
        self.last_sample_time = None

    def sample(self, value, sample_rate, timestamp=None):
        ts = time()
        self.samples.append((int(ts), value))
        self.last_sample_time = ts

    def _rate(self, sample1, sample2):
        interval = sample2[0] - sample1[0]
        if interval == 0:
            log.warn('Metric %s has an interval of 0. Not flushing.' % self.name)
            raise Infinity()

        delta = sample2[1] - sample1[1]
        if delta < 0:
            log.info('Metric %s has a rate < 0. Counter may have been Reset.' % self.name)
            raise UnknownValue()

        return (delta / float(interval))

    def flush(self, timestamp, interval):
        if len(self.samples) < 2:
            return []
        try:
            try:
                val = self._rate(self.samples[-2], self.samples[-1])
            except Exception:
                return []

            return [self.formatter(
                hostname=self.hostname,
                device_name=self.device_name,
                dimensions=self.dimensions,
                delegated_tenant=self.delegated_tenant,
                metric=self.name,
                value=val,
                timestamp=timestamp,
                metric_type=MetricTypes.GAUGE,
                interval=interval
            )]
        finally:
            self.samples = self.samples[-1:]
