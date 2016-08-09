# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
import unittest

import monasca_agent.common.metrics as metrics

SAMPLE_RATE = 1


class TestMetrics(unittest.TestCase):
    def test_Gauge(self):
        tenant_name = "test_gauge"
        metric_name = "foo"
        dimensions = {'a': 'b', 'c': 'd'}

        gauge = metrics.Gauge(metric_name, dimensions, tenant_name)

        gauge.sample(0, SAMPLE_RATE, 1)

        envelope = gauge.flush()[0]
        measurement = envelope['measurement']

        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 0)
        self.assertEqual(measurement['timestamp'], 1000)

        gauge.sample(1, SAMPLE_RATE, 2)

        envelope = gauge.flush()[0]
        measurement = envelope['measurement']

        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 1)
        self.assertEqual(measurement['timestamp'], 2000)

        gauge.sample(100.5212, SAMPLE_RATE, 125)

        envelope = gauge.flush()[0]
        measurement = envelope['measurement']

        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 100.5212)
        self.assertEqual(measurement['timestamp'], 125000)

        results = gauge.flush()
        self.assertEqual(results, [])

    def test_Counter(self):
        tenant_name = "test_counter"
        metric_name = "bar"
        dimensions = {'a': 1, 'c': 2}

        counter = metrics.Counter(metric_name, dimensions, tenant_name)

        counter.sample(5, SAMPLE_RATE, 1)

        envelope = counter.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 5)
        self.assertEqual(measurement['timestamp'], 1000)

        counter.sample(5, SAMPLE_RATE, 1)

        envelope = counter.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 5)
        self.assertEqual(measurement['timestamp'], 1000)

        counter.sample(5, SAMPLE_RATE, 1)
        counter.sample(5, SAMPLE_RATE, 1)

        envelope = counter.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 10)
        self.assertEqual(measurement['timestamp'], 1000)

        # Errors in counter report 0 value with previous timestamp
        counter.sample("WEGONI", SAMPLE_RATE, 2)
        envelope = counter.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 0)
        self.assertEqual(measurement['timestamp'], 1000)

    def test_Rate(self):
        tenant_name = "test_rate"
        metric_name = "baz"
        dimensions = {'a': 2, 'c': 3}

        rate = metrics.Rate(metric_name, dimensions, tenant_name)

        rate.sample(5, SAMPLE_RATE, 1)
        self.assertEqual(rate.flush(), [])

        rate.sample(5, SAMPLE_RATE, 2)

        envelope = rate.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 0.0)
        self.assertEqual(measurement['timestamp'], 2000)

        rate.sample(10, SAMPLE_RATE, 3)

        envelope = rate.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 5)
        self.assertEqual(measurement['timestamp'], 3000)

        rate.sample(12, SAMPLE_RATE, 3)
        self.assertEqual(rate.flush(), [])

        rate.sample(12, SAMPLE_RATE, 4)

        envelope = rate.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 0.0)
        self.assertEqual(measurement['timestamp'], 4000)

        rate.sample(14, SAMPLE_RATE, 5)

        envelope = rate.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 2)
        self.assertEqual(measurement['timestamp'], 5000)

        rate.sample(1, SAMPLE_RATE, 6)
        self.assertEqual(rate.flush(), [])
