# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP
import unittest

import monasca_agent.common.aggregator as aggregator
import monasca_agent.common.metrics as metrics_pkg

# a few valid characters to test
valid_name_chars = ".'_-"
invalid_name_chars = " <>={}(),\"\\\\;&"

# a few valid characters to test
valid_dimension_chars = " .'_-"
invalid_dimension_chars = "<>={}(),\"\\\\;&"


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

    def testValidNameChars(self):
        for c in valid_name_chars:
            self.submit_metric('test{}counter'.format(c), 2,
                               dimensions={"test-key": "test-value"})

    def testInvalidNameChars(self):
        for c in invalid_name_chars:
            self.submit_metric('test{}counter'.format(c), 2,
                               dimensions={"test-key": "test-value"},
                               exception=aggregator.InvalidMetricName)

    def testValidDimensionChars(self):
        for c in valid_dimension_chars:
            self.submit_metric('test-counter', 2,
                               dimensions={"test{}key".format(c): "test{}value".format(c)})

    def testInvalidDimensionChars(self):
        for c in invalid_dimension_chars:
            self.submit_metric('test-counter', 2,
                               dimensions={'test{}key'.format(c): 'test-value'},
                               exception=aggregator.InvalidDimensionKey)
            self.submit_metric('test-counter', 2,
                               dimensions={'test-key': 'test{}value'.format(c)},
                               exception=aggregator.InvalidDimensionValue)

    def testTooManyValueMeta(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {}
        for i in range(0, 17):
            value_meta['key{}'.format(i)] = 'value{}'.format(i)
        self.submit_metric("Foo",
                           2,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidValueMeta)

    def testEmptyValueMetaKey(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {'': 'BBB'}
        self.submit_metric("Foo",
                           2,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidValueMeta)

    def testEmptyValueMetaKey(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {'': 'BBB'}
        self.submit_metric("Foo",
                           2,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidValueMeta)

    def testTooLongValueMetaKey(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        key = "K"
        for i in range(0, aggregator.VALUE_META_NAME_MAX_LENGTH):
            key = "{}{}".format(key, "1")
        value_meta = {key: 'BBB'}
        print(key)
        self.submit_metric("Foo",
                           2,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidValueMeta)

    def testEmptyValueMetaKey(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {'': 'BBB'}
        self.submit_metric("Foo",
                           2,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidValueMeta)

    def testTooLargeValueMeta(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta_value = ""
        num_value_meta = 10
        for i in range(0, aggregator.VALUE_META_VALUE_MAX_LENGTH/num_value_meta):
            value_meta_value = '{}{}'.format(value_meta_value, '1')

        value_meta = {}
        for i in range(0, num_value_meta):
            value_meta['key{}'.format(i)] = value_meta_value
        self.submit_metric("Foo",
                           2,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=aggregator.InvalidValueMeta)
