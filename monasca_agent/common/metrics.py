# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
""" Metric data types
"""
import logging

log = logging.getLogger(__name__)


class Metric(object):
    """A base metric class """

    def __init__(self, name, dimensions, tenant):
        self.metric = {'name': name,
                       'dimensions': dimensions.copy()}

        self.value_meta = None
        self.value = None
        self.timestamp = None
        self.tenant = tenant

    def measurement(self, value, timestamp):
        measurement = self.metric.copy()

        if self.value_meta:
            measurement['value_meta'] = self.value_meta.copy()
        else:
            measurement['value_meta'] = None

        measurement['value'] = value
        measurement['timestamp'] = timestamp * 1000

        envelope = {'measurement': measurement,
                    'tenant_id': self.tenant}

        return envelope

    def sample(self, value, sample_rate, timestamp):
        """Save a sample. """
        raise NotImplementedError()

    def flush(self):
        """Flush current sample. """
        raise NotImplementedError()


class Gauge(Metric):
    """A metric that tracks a value at particular points in time. """

    def __init__(self, name, dimensions, tenant=None):
        super(Gauge, self).__init__(name, dimensions, tenant)

    def sample(self, value, sample_rate, timestamp):
        self.value = value
        self.timestamp = timestamp

    def flush(self):
        # 0 is a valid value, so can't do: if not self.value:
        if self.value is None:
            return []

        envelope = self.measurement(self.value, self.timestamp)
        self.value = None
        return [envelope]


class Counter(Metric):
    """A metric that tracks a counter value. """

    def __init__(self, name, dimensions, tenant=None):
        super(Counter, self).__init__(name, dimensions, tenant)
        self.value = 0

    def sample(self, value, sample_rate, timestamp):
        try:
            self.value += value * int(1 / sample_rate)
            self.timestamp = timestamp
        except TypeError:
            log.error("metric {} value {} sample_rate {}".
                      format(self.metric['name'], value, sample_rate))

    def flush(self):
        envelope = self.measurement(self.value, self.timestamp)
        self.value = 0
        return [envelope]


class Rate(Metric):
    """Track the rate of metrics over each flush interval """

    def __init__(self, name, dimensions, tenant=None):
        super(Rate, self).__init__(name, dimensions, tenant)
        self.samples = []

    def sample(self, value, sample_rate, timestamp):
        self.samples.append((int(timestamp), value))
        self.timestamp = timestamp

        if len(self.samples) < 2:
            self.value = None
        else:
            self.value = self._rate(self.samples[-2], self.samples[-1])
            self.samples = self.samples[-1:]

    def _rate(self, sample1, sample2):
        delta_t = sample2[0] - sample1[0]
        delta_v = sample2[1] - sample1[1]
        rate = None
        if delta_v < 0:
            log.debug('Metric {0} has a rate < 0. New value = {1} and old '
                      'value = {2}. Counter may have been Reset.'.
                      format(self.metric['name'], sample2[1], sample1[1]))
            return rate
        try:
            rate = delta_v / float(delta_t)
        except ZeroDivisionError as e:
            log.exception('Error in sampling metric {0}, time difference '
                          'between current time and last_update time is '
                          '0, returned {1}'.
                          format(self.metric['name'], e))
        return rate

    def flush(self):
        if self.value is None:
            return []

        envelope = self.measurement(self.value, self.timestamp)
        self.value = None
        return [envelope]
