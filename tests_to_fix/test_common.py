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

import time
import unittest
import logging
logger = logging.getLogger()
from monasca_agent.common.exceptions import UnknownValue, CheckException, Infinity
from monasca_agent.collector.checks.check import Check
from monasca_agent.common.aggregator import MetricsAggregator


class TestCore(unittest.TestCase):

    "Tests to validate the core check logic"

    def setUp(self):
        self.c = Check(logger)
        self.c.gauge("test-metric")
        self.c.counter("test-counter")

    def test_gauge(self):
        self.assertEqual(self.c.is_gauge("test-metric"), True)
        self.assertEqual(self.c.is_counter("test-metric"), False)
        self.c.save_sample("test-metric", 1.0)
        # call twice in a row, should be invariant
        self.assertEqual(self.c.get_sample("test-metric"), 1.0)
        self.assertEqual(self.c.get_sample("test-metric"), 1.0)
        self.assertEqual(self.c.get_sample_with_timestamp("test-metric")[1], 1.0)
        # new value, old one should be gone
        self.c.save_sample("test-metric", 2.0)
        self.assertEqual(self.c.get_sample("test-metric"), 2.0)
        self.assertEqual(len(self.c._sample_store["test-metric"]), 1)
        # with explicit timestamp
        self.c.save_sample("test-metric", 3.0, 1298066183.607717)
        self.assertEqual(self.c.get_sample_with_timestamp(
            "test-metric"), (1298066183.607717, 3.0, None, None))
        # get_samples()
        self.assertEqual(self.c.get_samples(), {"test-metric": 3.0})

    def testEdgeCases(self):
        self.assertRaises(UnknownValue, self.c.get_sample, "unknown-metric")
        # same value
        self.c.save_sample("test-counter", 1.0, 1.0)
        self.c.save_sample("test-counter", 1.0, 1.0)
        self.assertRaises(Infinity, self.c.get_sample, "test-counter")

    def test_counter(self):
        self.c.save_sample("test-counter", 1.0, 1.0)
        self.assertRaises(UnknownValue, self.c.get_sample, "test-counter", expire=False)
        self.c.save_sample("test-counter", 2.0, 2.0)
        self.assertEqual(self.c.get_sample("test-counter", expire=False), 1.0)
        self.assertEqual(self.c.get_sample_with_timestamp(
            "test-counter", expire=False), (2.0, 1.0, None, None))
        self.assertEqual(self.c.get_samples(expire=False), {"test-counter": 1.0})
        self.c.save_sample("test-counter", -2.0, 3.0)
        self.assertRaises(UnknownValue, self.c.get_sample_with_timestamp, "test-counter")

    def test_dimensions(self):
        # Test metric dimensions
        now = int(time.time())
        # dimensions metrics
        self.c.save_sample(
            "test-counter", 1.0, 1.0, dimensions={"dim1": "value1", "dim2": "value2"})
        self.c.save_sample(
            "test-counter", 2.0, 2.0, dimensions={"dim1": "value1", "dim2": "value2"})
        # Only 1 point recording for this combination of dimensions, won't be sent
        self.c.save_sample(
            "test-counter", 3.0, 3.0, dimensions={"dim1": "value1", "dim3": "value3"})
        self.c.save_sample("test-metric", 3.0, now, dimensions={"dim3": "value3", "dim4": "value4"})
        # Arg checks
        self.assertRaises(
            CheckException, self.c.save_sample, "test-metric", 4.0, now + 5, dimensions="abc")
        # This is a different combination of dimensions
        self.c.save_sample("test-metric", 3.0, now, dimensions={"dim5": "value5", "dim3": "value3"})
        results = sorted(self.c.get_metrics())
        self.assertEqual(results,
                         [("test-counter", 2.0, 1.0, {"dimensions": {"dim1": "value1", "dim2": "value2"}}),
                          ("test-metric", now, 3.0,
                           {"dimensions": {"dim3": "value3", "dim4": "value4"}}),
                          ("test-metric", now, 3.0,
                           {"dimensions": {"dim3": "value3", "dim5": "value5"}})
                          ])
        # dimensions metrics are not available through get_samples anymore
        self.assertEqual(self.c.get_samples(), {})

    def test_samples(self):
        self.assertEqual(self.c.get_samples(), {})
        self.c.save_sample("test-metric", 1.0, 0.0)  # value, ts
        self.c.save_sample("test-counter", 1.0, 1.0)  # value, ts
        self.c.save_sample("test-counter", 4.0, 2.0)  # value, ts
        assert "test-metric" in self.c.get_samples_with_timestamps(
            expire=False), self.c.get_samples_with_timestamps(expire=False)
        self.assertEqual(self.c.get_samples_with_timestamps(
            expire=False)["test-metric"], (0.0, 1.0, None, None))
        assert "test-counter" in self.c.get_samples_with_timestamps(
            expire=False), self.c.get_samples_with_timestamps(expire=False)
        self.assertEqual(self.c.get_samples_with_timestamps(
            expire=False)["test-counter"], (2.0, 3.0, None, None))

    def test_name(self):
        self.assertEqual(self.c.normalize("metric"), "metric")
        self.assertEqual(self.c.normalize("metric", "prefix"), "prefix.metric")
        self.assertEqual(self.c.normalize("__metric__", "prefix"), "prefix.metric")
        self.assertEqual(
            self.c.normalize("abc.metric(a+b+c{}/5)", "prefix"), "prefix.abc.metric_a_b_c_5")
        self.assertEqual(
            self.c.normalize(
                "VBE.default(127.0.0.1,,8080).happy",
                "varnish"),
            "varnish.VBE.default_127.0.0.1_8080.happy")


class TestAggregator(unittest.TestCase):

    def setUp(self):
        self.aggr = MetricsAggregator('test-aggr')

    def test_dupe_tags(self):
        self.aggr.increment('test-counter', 1, dimensions={'a': 'avalue', 'b': 'bvalue'})
        self.aggr.increment(
            'test-counter', 1, dimensions={'a': 'avalue', 'b': 'bvalue', 'b': 'bvalue'})
        self.assertEqual(len(self.aggr.metrics), 1, self.aggr.metrics)
        metric = list(self.aggr.metrics.values())[0]
        self.assertEqual(metric.value, 2)

if __name__ == '__main__':
    unittest.main()
