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

import unittest
import time
import threading
import os

from nose.plugins.skip import SkipTest

from monasca_agent.common.aggregator import MetricsAggregator
from monasca_agent.statsd import Server
from monasca_agent.common.util import PidFile
from monasca_agent.common.config import get_logging_config
from monasca_agent.collector.jmxfetch import JMXFetch


STATSD_PORT = 8129


class DummyReporter(threading.Thread):

    def __init__(self, metrics_aggregator):
        threading.Thread.__init__(self)
        self.finished = threading.Event()
        self.metrics_aggregator = metrics_aggregator
        self.interval = 10
        self.metrics = None
        self.finished = False
        self.start()

    def run(self):
        while not self.finished:
            time.sleep(self.interval)
            self.flush()

    def flush(self):
        metrics = self.metrics_aggregator.flush()
        if metrics:
            self.metrics = metrics


class JMXTestCase(unittest.TestCase):

    def setUp(self):
        aggregator = MetricsAggregator("test_host")
        self.server = Server(aggregator, "localhost", STATSD_PORT)
        self.reporter = DummyReporter(aggregator)

        self.t1 = threading.Thread(target=self.server.start)
        self.t1.start()

        confd_path = os.path.realpath(os.path.join(os.path.abspath(__file__), "..", "jmx_yamls"))
        JMXFetch.init(confd_path, {'dogstatsd_port': STATSD_PORT}, get_logging_config(), 15)

    def tearDown(self):
        self.server.stop()
        self.reporter.finished = True
        JMXFetch.stop()

    def testCustomJMXMetric(self):
        raise SkipTest('Requires running JMX')
        count = 0
        while self.reporter.metrics is None:
            time.sleep(1)
            count += 1
            if count > 20:
                raise Exception("No metrics were received in 20 seconds")

        metrics = self.reporter.metrics

        self.assertIsInstance(metrics, list)
        self.assertTrue(len(metrics) > 0)
        self.assertEqual(len([t for t in metrics if t[
                         'metric'] == "my.metric.buf" and "instance:jmx_instance1" in t['dimensions']]), 2, metrics)
        self.assertTrue(len([t for t in metrics if 'type:ThreadPool' in t[
                        'dimensions'] and "instance:jmx_instance1" in t['dimensions'] and "jmx.catalina" in t['metric']]) > 8, metrics)
        self.assertTrue(len([t for t in metrics if "jvm." in t['metric']
                             and "instance:jmx_instance1" in t['dimensions']]) == 7, metrics)


if __name__ == "__main__":
    unittest.main()
