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
from nose.plugins.skip import SkipTest


class GearmanTestCase(unittest.TestCase):

    def testMetrics(self):
        raise SkipTest('Requires Gearman')

        config = {
            'instances': [{
                'dimensions': {'first': 'second'}
            }]
        }
        agent_config = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.check = load_check('gearmand', config, agent_config)

        self.check.check(config['instances'][0])

        metrics = self.check.get_metrics()
        self.assertIsInstance(metrics, list)
        self.assertTrue(len(metrics) == 4)
        self.assertTrue(len([k for k in metrics if "second" in k[3]['dimensions']['first']]) == 4)
