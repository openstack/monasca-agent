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
from tests.common import load_check

from nose.plugins.attrib import attr
from nose.plugins.skip import SkipTest


class CouchbaseTestCase(unittest.TestCase):

    def setUp(self):
        self.config = {
            'instances': [{
                'server': 'http://localhost:8091',
                'user': 'Administrator',
                'password': 'password',
            }]
        }
        self.agent_config = {
            'version': '0.1',
            'api_key': 'toto'
        }
        self.check = load_check('couchbase', self.config, self.agent_config)

    @attr('couchbase')
    def test_camel_case_to_joined_lower(self):
        test_pairs = {
            'camelCase': 'camel_case',
            'FirstCapital': 'first_capital',
            'joined_lower': 'joined_lower',
            'joined_Upper1': 'joined_upper1',
            'Joined_upper2': 'joined_upper2',
            'Joined_Upper3': 'joined_upper3',
            '_leading_Underscore': 'leading_underscore',
            'Trailing_Underscore_': 'trailing_underscore',
            'DOubleCAps': 'd_ouble_c_aps',
            '@@@super--$$-Funky__$__$$%': 'super_funky',
        }

        for test_input, expected_output in test_pairs.items():
            test_output = self.check.camel_case_to_joined_lower(test_input)
            self.assertEqual(
                test_output,
                expected_output,
                'Input was %s, expected output was %s, actual output was %s' %
                (test_input,
                 expected_output,
                 test_output))

    @attr('couchbase')
    def test_metrics_casing(self):
        raise SkipTest("Skipped for now as it's hard to configure couchbase on travis")
        self.check.check(self.config['instances'][0])

        metrics = self.check.get_metrics()

        camel_cased_metrics = [u'couchbase.hdd.used_by_data',
                               u'couchbase.ram.used_by_data',
                               u'couchbase.ram.quota_total',
                               u'couchbase.ram.quota_used',
                               ]

        found_metrics = [k[0] for k in metrics if k[0] in camel_cased_metrics]
        self.assertEqual(found_metrics.sort(), camel_cased_metrics.sort())

    @attr('couchbase')
    def test_metrics(self):
        raise SkipTest("Skipped for now as it's hard to configure couchbase on travis")
        self.check.check(self.config['instances'][0])

        metrics = self.check.get_metrics()

        self.assertTrue(isinstance(metrics, list), metrics)
        self.assertTrue(len(metrics) > 3)
        self.assertTrue(
            len([k for k in metrics if "instance:http://localhost:8091" in k[3]['dimensions']]) > 3)

        self.assertTrue(len([k for k in metrics if -1 != k[0].find('by_node')])
                        > 1, 'Unable to fund any per node metrics')
        self.assertTrue(len([k for k in metrics if -1 != k[0].find('by_bucket')])
                        > 1, 'Unable to fund any per node metrics')
