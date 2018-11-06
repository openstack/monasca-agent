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
        if self.timestamp is None:
            return []
        if self.value is None:
            log.error('Value of None is not supported, will not send. '
                      'Metric %s with dimensions %s at time %d',
                      self.metric['name'],
                      self.metric['dimensions'],
                      self.timestamp)
            return []

        envelope = self.measurement(self.value, self.timestamp)
        self.timestamp = None
        self.value = None
        return [envelope]


class Gauge(Metric):
    """A metric that tracks a value at particular points in time. """

    def __init__(self, name, dimensions, tenant=None):
        super(Gauge, self).__init__(name, dimensions, tenant)

    def sample(self, value, sample_rate, timestamp):
        self.value = value
        self.timestamp = timestamp


class Counter(Metric):
    """A metric that tracks a counter value. """

    def __init__(self, name, dimensions, tenant=None):
        super(Counter, self).__init__(name, dimensions, tenant)

    def sample(self, value, sample_rate, timestamp):
        try:
            inc = float(value) / sample_rate
            if self.timestamp is None:
                self.value = inc
            else:
                self.value += inc
            self.timestamp = timestamp
        except (TypeError, ValueError):
            log.exception("illegal metric {} value {} sample_rate {}".
                          format(self.metric['name'], value, sample_rate))

    # redefine flush method to make counter an integer when sample rates <> 1.0 used
    def flush(self):
        if self.timestamp:
            self.value = int(self.value)
            return super(Counter, self).flush()
        else:
            return []


class Rate(Metric):
    """Track the rate of metrics over each flush interval """

    def __init__(self, name, dimensions, tenant=None):
        super(Rate, self).__init__(name, dimensions, tenant)
        self.start_value = None
        self.start_timestamp = None

    def sample(self, value, sample_rate, timestamp):
        # set first value if missing
        if self.start_timestamp is None:
            self.start_timestamp = timestamp
            self.start_value = value
        # set second value otherwise
        else:
            self.timestamp = timestamp
            self.value = value

    # redefine flush method to calculate rate from metrics
    def flush(self):
        # need at least two timestamps to determine rate
        # is the second one is missing then the first is kept as start value for the subsequent interval
        if self.start_timestamp is None or self.timestamp is None:
            return []

        delta_t = self.timestamp - self.start_timestamp
        delta_v = self.value - self.start_value
        try:
            rate = delta_v / float(delta_t)
        except ZeroDivisionError:
            log.warning('Conflicting values reported for metric %s with dimensions %s at time %d: (%f, %f)', self.metric['name'],
                        self.metric['dimensions'], self.timestamp, self.start_value, self.value)

            # skip this measurement, but keep value for next cycle
            self.start_value = self.value
            return []

        # make it start value for next interval (even if it is None!)
        self.start_value = self.value
        self.start_timestamp = self.timestamp

        envelope = self.measurement(rate, self.timestamp)
        self.timestamp = None
        self.value = None
        return [envelope]
