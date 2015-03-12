""" Metric data types
"""
from collections import namedtuple
import logging
from time import time

from monasca_agent.common.exceptions import Infinity, UnknownValue


log = logging.getLogger(__name__)


class Measurement(object):
    def __init__(self, name, timestamp, value, dimensions, delegated_tenant=None):
        self.name = name
        self.timestamp = timestamp
        self.value = value
        self.dimensions = dimensions.copy()
        self.delegated_tenant = delegated_tenant


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

    def flush(self, timestamp):
        """ Flush all metrics up to the given timestamp. """
        raise NotImplementedError()


class Gauge(Metric):

    """ A metric that tracks a value at particular points in time. """

    def __init__(self, formatter, name, dimensions,
                 hostname, device_name, delegated_tenant=None):
        self.formatter = formatter
        self.name = name
        self.value = None
        self.dimensions = dimensions.copy()
        self.delegated_tenant = delegated_tenant
        self.hostname = hostname
        self.device_name = device_name
        self.timestamp = time()

    def sample(self, value, sample_rate, timestamp=None):
        self.value = value
        self.timestamp = timestamp

    def flush(self, timestamp):
        if self.value is not None:
            res = [self.formatter(
                metric=self.name,
                timestamp=self.timestamp or timestamp,
                value=self.value,
                dimensions=self.dimensions,
                delegated_tenant=self.delegated_tenant,
                hostname=self.hostname,
                device_name=self.device_name,
                metric_type=MetricTypes.GAUGE
            )]
            self.value = None
            return res

        return []


class Counter(Metric):

    """ A metric that tracks a counter value. """

    def __init__(self, formatter, name, dimensions,
                 hostname, device_name, delegated_tenant=None):
        self.formatter = formatter
        self.name = name
        self.value = 0
        self.dimensions = dimensions.copy()
        self.delegated_tenant = delegated_tenant
        self.hostname = hostname
        self.device_name = device_name

    def sample(self, value, sample_rate, timestamp=None):
        self.value += value * int(1 / sample_rate)

    def flush(self, timestamp):
        try:
            return [self.formatter(
                metric=self.name,
                value=self.value,
                timestamp=timestamp,
                dimensions=self.dimensions,
                delegated_tenant=self.delegated_tenant,
                hostname=self.hostname,
                device_name=self.device_name,
                metric_type=MetricTypes.RATE
            )]
        finally:
            self.value = 0


class Histogram(Metric):

    """ A metric to track the distribution of a set of values. """

    def __init__(self, formatter, name, dimensions,
                 hostname, device_name, delegated_tenant=None):
        self.formatter = formatter
        self.name = name
        self.count = 0
        self.samples = []
        self.percentiles = [0.95]
        self.dimensions = dimensions.copy()
        self.delegated_tenant = delegated_tenant
        self.hostname = hostname
        self.device_name = device_name

    def sample(self, value, sample_rate, timestamp=None):
        self.count += int(1 / sample_rate)
        self.samples.append(value)

    def flush(self, ts):
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
            ('count', self.count, MetricTypes.RATE)
        ]

        metrics = [self.formatter(
            hostname=self.hostname,
            device_name=self.device_name,
            dimensions=self.dimensions,
            delegated_tenant=self.delegated_tenant,
            metric='%s.%s' % (self.name, suffix),
            value=value,
            timestamp=ts,
            metric_type=metric_type
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
                metric_type=MetricTypes.GAUGE
            ))

        # Reset our state.
        self.samples = []
        self.count = 0

        return metrics


class Set(Metric):

    """ A metric to track the number of unique elements in a set. """

    def __init__(self, formatter, name, dimensions,
                 hostname, device_name, delegated_tenant=None):
        self.formatter = formatter
        self.name = name
        self.dimensions = dimensions.copy()
        self.delegated_tenant = delegated_tenant
        self.hostname = hostname
        self.device_name = device_name
        self.values = set()

    def sample(self, value, sample_rate, timestamp=None):
        self.values.add(value)

    def flush(self, timestamp):
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
                metric_type=MetricTypes.GAUGE
            )]
        finally:
            self.values = set()


class Rate(Metric):

    """ Track the rate of metrics over each flush interval """

    def __init__(self, formatter, name, dimensions,
                 hostname, device_name, delegated_tenant=None):
        self.formatter = formatter
        self.name = name
        self.dimensions = dimensions.copy()
        self.delegated_tenant = delegated_tenant
        self.hostname = hostname
        self.device_name = device_name
        self.samples = []

    def sample(self, value, sample_rate, timestamp=None):
        if not timestamp:
            timestamp = time()
        self.samples.append((int(timestamp), value))

    def _rate(self, sample1, sample2):
        rate_interval = sample2[0] - sample1[0]
        if rate_interval == 0:
            log.warn('Metric %s has an interval of 0. Not flushing.' % self.name)
            raise Infinity()

        delta = sample2[1] - sample1[1]
        if delta < 0:
            log.info('Metric %s has a rate < 0. Counter may have been Reset.' % self.name)
            raise UnknownValue()

        return (delta / float(rate_interval))

    def flush(self, timestamp):
        if len(self.samples) < 2:
            return []
        try:
            val = self._rate(self.samples[-2], self.samples[-1])
            self.samples = self.samples[-1:]
        except Exception:
            log.warn('Error flushing {0} sample.'.format(self.name))
            return []

        return [self.formatter(hostname=self.hostname,
           device_name=self.device_name,
           dimensions=self.dimensions,
           delegated_tenant=self.delegated_tenant,
           metric=self.name,
           value=val,
           timestamp=timestamp,
           metric_type=MetricTypes.GAUGE)]
