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

	# single counter value
        counter.sample(5, SAMPLE_RATE, 1)

        envelope = counter.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 5)
        self.assertEqual(measurement['timestamp'], 1000)

	# multiple counter value with different timestamps: add 
        counter.sample(5, SAMPLE_RATE, 1)
	counter.sample(6, SAMPLE_RATE, 2)

        envelope = counter.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 11)
        self.assertEqual(measurement['timestamp'], 2000)

        # multiple counter values with same timestamp: add
        counter.sample(5, SAMPLE_RATE, 3)
        counter.sample(5, SAMPLE_RATE, 3)

        envelope = counter.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 5+5)
        self.assertEqual(measurement['timestamp'], 3000)

        # Invalid metric values: ignore
        counter.sample("WEGONI", SAMPLE_RATE, 2)
        results = counter.flush()
        self.assertEqual(results, [])

    def test_Rate(self):
        tenant_name = "test_rate"
        metric_name = "baz"
        dimensions = {'a': 2, 'c': 3}

        rate = metrics.Rate(metric_name, dimensions, tenant_name)

	# single sample without predecessor: no rate can be calculated
        rate.sample(5, SAMPLE_RATE, 1)
        self.assertEqual(rate.flush(), [])

	# zero difference between samples: rate 0
        rate.sample(5, SAMPLE_RATE, 2)

        envelope = rate.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 0.0)
        self.assertEqual(measurement['timestamp'], 2000)

	# samples (5,10) in 1 sec interval: rate 5/sec. 
        rate.sample(10, SAMPLE_RATE, 3)

        envelope = rate.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 5)
        self.assertEqual(measurement['timestamp'], 3000)

	# conflicting values for same timestamp: no result, but keep last sample for next rate calc.
        rate.sample(12, SAMPLE_RATE, 3)
        self.assertEqual(rate.flush(), [])

	# zero difference between samples, incomplete previous interval T: rate 0/sec.
        rate.sample(12, SAMPLE_RATE, 4)

        envelope = rate.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 0.0)
        self.assertEqual(measurement['timestamp'], 4000)

	# several samples (13, 14) in interval, take last values of T1 and T0 for rate calc: rate = (14-12)/(6-4)
        rate.sample(13, SAMPLE_RATE, 5)
	rate.sample(14, SAMPLE_RATE, 6)

        envelope = rate.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 1)
        self.assertEqual(measurement['timestamp'], 6000)

	# negative rate: often result of a restart, but that should not be hidden
        rate.sample(1, SAMPLE_RATE, 7)

        envelope = rate.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], -13)
        self.assertEqual(measurement['timestamp'], 7000)

	# recover from negative rate
	rate.sample(2, SAMPLE_RATE, 8)

        envelope = rate.flush()[0]
        measurement = envelope['measurement']
        self.assertEqual(envelope['tenant_id'], tenant_name)
        self.assertEqual(measurement['name'], metric_name)
        self.assertEqual(measurement['dimensions'], dimensions)
        self.assertEqual(measurement['value'], 1)
        self.assertEqual(measurement['timestamp'], 8000)
	
