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

"""
Run the following on your local SQL Server:

CREATE LOGIN datadog WITH PASSWORD = '340$Uuxwp7Mcxo7Khy';
CREATE USER datadog FOR LOGIN datadog;
GRANT SELECT on sys.dm_os_performance_counters to datadog;
GRANT VIEW SERVER STATE to datadog;
"""

CONFIG = """
init_config:
    custom_metrics:
        -   name: sqlserver.clr.execution
            type: gauge
            counter_name: CLR Execution

        -   name: sqlserver.exec.in_progress
            type: gauge
            counter_name: OLEDB calls
            instance_name: Cumulative execution time (ms) per second

        -   name: sqlserver.db.commit_table_entries
            type: gauge
            counter_name: Log Flushes/sec
            instance_name: ALL
            tag_by: db

instances:
    -   host: 127.0.0.1,1433
        username: datadog
        password: 340$Uuxwp7Mcxo7Khy
"""


class SQLServerTestCase(unittest.TestCase):

    @attr('windows')
    def testSqlServer(self):
        raise SkipTest('Requires adodbapi')
        check, instances = get_check('sqlserver', CONFIG)
        check.check(instances[0])
        metrics = check.get_metrics()

        # Make sure the base metrics loaded
        base_metrics = [m[0] for m in check.METRICS]
        ret_metrics = [m[0] for m in metrics]
        for metric in base_metrics:
            assert metric in ret_metrics

        # Check our custom metrics
        assert 'sqlserver.clr.execution' in ret_metrics
        assert 'sqlserver.exec.in_progress' in ret_metrics
        assert 'sqlserver.db.commit_table_entries' in ret_metrics

        # Make sure the ALL custom metric is tagged
        tagged_metrics = [m for m in metrics
                          if m[0] == 'sqlserver.db.commit_table_entries']
        for metric in tagged_metrics:
            for tag in metric[3]['dimensions']:
                assert tag.startswith('db')

if __name__ == "__main__":
    unittest.main()
