# (C) Copyright 2015-2017 Hewlett Packard Enterprise Development Company LP
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

import six

import monasca_agent.common.aggregator as aggregator
import monasca_agent.common.metrics as metrics_pkg

import monasca_common.validation.metrics as metric_validator

# a few valid characters to test
valid_name_chars = ".'_-"
invalid_name_chars = metric_validator.INVALID_CHARS

# a few valid characters to test
valid_dimension_chars = " .'_-"
invalid_dimension_chars = metric_validator.INVALID_CHARS


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
        dimensions = {six.unichr(2440): 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta)

    def testValidMetricUnicodeDimensionKey(self):
        dimensions = {'A': 'B', 'B': six.unichr(920), 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta)

    def testValidMetricUnicodeMetricName(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric(six.unichr(6021),
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
                           exception=metric_validator.InvalidMetricName)

    def testInvalidMetricNameEmpty(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric('',
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidMetricName)

    def testInvalidMetricNameNonStr(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric(133,
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidMetricName)

    def testInvalidMetricRestrictedCharacters(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric('"Foo"',
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidMetricName)

    def testInvalidDimensionEmptyKey(self):
        dimensions = {'A': 'B', '': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidDimensionKey)

    def testInvalidDimensionEmptyValue(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': ''}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidDimensionValue)

    def testInvalidDimensionNonStrKey(self):
        dimensions = {'A': 'B', 4: 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidDimensionKey)

    def testInvalidDimensionNonStrValue(self):
        dimensions = {'A': 13.3, 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidDimensionValue)

    def testInvalidDimensionKeyLength(self):
        dimensions = {'A'*256: 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidDimensionKey)

    def testInvalidDimensionValueLength(self):
        dimensions = {'A': 'B', 'B': 'C'*256, 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidDimensionValue)

    def testValidDimensionKeyParenthesesCharacter(self):
        dimensions = {'A': 'B', 'B': 'C', '(D)': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta)

    def testInvalidDimensionValueRestrictedCharacters(self):
        dimensions = {'A': 'B;', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidDimensionValue)

    def testInvalidDimensionKeyLeadingUnderscore(self):
        dimensions = {'_A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           5,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidDimensionKey)

    def testInvalidValue(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {"This is a test": "test, test, test"}
        self.submit_metric("Foo",
                           "value",
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidValue)

    def testValidNameChars(self):
        for c in valid_name_chars:
            self.submit_metric('test{}counter'.format(c), 2,
                               dimensions={"test-key": "test-value"})

    def testInvalidNameChars(self):
        for c in invalid_name_chars:
            self.submit_metric('test{}counter'.format(c), 2,
                               dimensions={"test-key": "test-value"},
                               exception=metric_validator.InvalidMetricName)

    def testValidDimensionChars(self):
        for c in valid_dimension_chars:
            self.submit_metric('test-counter', 2,
                               dimensions={"test{}key".format(c): "test{}value".format(c)})

    def testInvalidDimensionChars(self):
        for c in invalid_dimension_chars:
            self.submit_metric('test-counter', 2,
                               dimensions={'test{}key'.format(c): 'test-value'},
                               exception=metric_validator.InvalidDimensionKey)
            self.submit_metric('test-counter', 2,
                               dimensions={'test-key': 'test{}value'.format(c)},
                               exception=metric_validator.InvalidDimensionValue)

    def testTooManyValueMeta(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {}
        for i in range(0, 17):
            value_meta['key{}'.format(i)] = 'value{}'.format(i)
        self.submit_metric("Foo",
                           2,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidValueMeta)

    def testEmptyValueMetaKey(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta = {'': 'BBB'}
        self.submit_metric("Foo",
                           2,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidValueMeta)

    def testTooLongValueMetaKey(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        key = "K"
        for i in range(0, metric_validator.VALUE_META_NAME_MAX_LENGTH):
            key = "{}{}".format(key, "1")
        value_meta = {key: 'BBB'}
        print(key)
        self.submit_metric("Foo",
                           2,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidValueMeta)

    def testTooLargeValueMeta(self):
        dimensions = {'A': 'B', 'B': 'C', 'D': 'E'}
        value_meta_value = ""
        num_value_meta = 10
        for i in range(0, metric_validator.VALUE_META_VALUE_MAX_LENGTH//num_value_meta):
            value_meta_value = '{}{}'.format(value_meta_value, '1')

        value_meta = {}
        for i in range(0, num_value_meta):
            value_meta['key{}'.format(i)] = value_meta_value
        self.submit_metric("Foo",
                           2,
                           dimensions=dimensions,
                           value_meta=value_meta,
                           exception=metric_validator.InvalidValueMeta)
