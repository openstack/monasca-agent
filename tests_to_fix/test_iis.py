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
import logging
from nose.plugins.attrib import attr
from nose.plugins.skip import SkipTest

from tests.common import get_check

logging.basicConfig()

CONFIG = """
init_config:

instances:
    -   host: .
        dimensions:
            dim1: value1
            dim2: value2
"""


class IISTestCase(unittest.TestCase):

    @attr('windows')
    def testIIS(self):
        raise SkipTest('Requires IIS and wmi')
        check, instances = get_check('iis', CONFIG)
        check.check(instances[0])
        metrics = check.get_metrics()

        base_metrics = [m[0] for m in check.METRICS]
        ret_metrics = [m[0] for m in metrics]
        ret_dimensions = [m[3]['dimensions'] for m in metrics]

        # Make sure each metric was captured
        for metric in base_metrics:
            assert metric in ret_metrics

        # Make sure everything is tagged correctly
        for dimensions in ret_dimensions:
            assert dimensions == {'dim1': 'value1', 'dim2': 'value2'}

if __name__ == "__main__":
    unittest.main()
