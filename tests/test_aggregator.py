import unittest

import monasca_agent.common.aggregator as aggregator
import monasca_agent.common.metrics as metrics_pkg


class TestMetricsAggregator(unittest.TestCase):
    def setUp(self):
        self.aggregator = aggregator.MetricsAggregator("Foo")

    def submit_metric(self, name, value,
                      dimensions=None,
                      value_meta=None,
                      exception=None):
        if exception:
            with self.assertRaises(exception):
                self.aggregator.submit_metric(name,
                                              value,
                                              metrics_pkg.Gauge,
                                              dimensions=dimensions,
                                              delegated_tenant=None,
                                              hostname=None,
                                              device_name=None,
                                              value_meta=value_meta)
        else:
            self.aggregator.submit_metric(name,
                                          value,
                                          metrics_pkg.Gauge,
                                          dimensions=dimensions,
                                          delegated_tenant=None,
                                          hostname=None,
                                          device_name=None,
                                          value_meta=value_meta)

    def testValidMetric(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta)

    def testValidMetricUnicodeDimensionValue(self):
        dimensions = {unichr(2440): 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta)

    def testValidMetricUnicodeDimensionKey(self):
        dimensions = {'A': 'B', 'B': unichr(920), 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta)

    def testValidMetricUnicodeMetricName(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric(unichr(6021),
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta)

    def testInvalidMetricName(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("TooLarge" * 255,
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidMetricName)

    def testInvalidMetricNameEmpty(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric('',
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidMetricName)

    def testInvalidMetricNameNonStr(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric(133,
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidMetricName)

    def testInvalidMetricRestrictedCharacters(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric('"Foo"',
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidMetricName)

    def testInvalidDimensionEmptyKey(self):
        dimensions = {'A': 'B', '': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidDimensionKey)

    def testInvalidDimensionEmptyValue(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': ''}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidDimensionValue)

    def testInvalidDimensionNonStrKey(self):
        dimensions = {'A': 'B', 4: 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidDimensionKey)

    def testInvalidDimensionNonStrValue(self):
        dimensions = {'A': 13.3, 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidDimensionValue)

    def testInvalidDimensionKeyLength(self):
        dimensions = {'A'*256: 'B', 'B': 'C', 'D': 'E'}
        print dimensions
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidDimensionKey)

    def testInvalidDimensionValueLength(self):
        dimensions = {'A': 'B', 'B': 'C'*256, 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidDimensionValue)

    def testInvalidDimensionKeyRestrictedCharacters(self):
        dimensions = {'A': 'B', 'B': 'C', '(D)': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidDimensionKey)

    def testInvalidDimensionValueRestrictedCharacters(self):
        dimensions = {'A': 'B;', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidDimensionValue)

    def testInvalidDimensionKeyLeadingUnderscore(self):
        dimensions = {'_A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidDimensionKey)

    def testInvalidValue(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           "value",
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidValue)
