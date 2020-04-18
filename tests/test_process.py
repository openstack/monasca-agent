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

from unittest import mock
import unittest

from tests.common import load_check


class TestSimpleProcess(unittest.TestCase):
    def setUp(self):
        self.psutil_process_iter_patcher = mock.patch('psutil.process_iter')

        self.mock_process_iter = self.psutil_process_iter_patcher.start()

        process_attrs = {
            'name': 'process_name',
            'pid': 1234,
            'username': 'user',
            'cmdline': '/usr/bin/process_name'
        }
        process = mock.Mock()
        process.as_dict.return_value = process_attrs
        self.mock_process_iter.return_value = [process]

        config = {'init_config': {},
                  'instances': [{'name': 'test',
                                 'search_string': ['process_name'],
                                 'detailed': False}]}
        self.check = load_check('process', config)

    def tearDown(self):
        self.psutil_process_iter_patcher.stop()

    def testPidCount(self):
        self.check.run()
        metrics = self.check.get_metrics()

        self.assertEqual(1, len(metrics))
        self.assertEqual('process.pid_count', metrics[0]['measurement']['name'])


class TestDetailedProcess(unittest.TestCase):
    def setUp(self):
        self.psutil_process_patcher = mock.patch('psutil.Process')
        self.psutil_process_iter_patcher = mock.patch('psutil.process_iter')

        self.mock_process = self.psutil_process_patcher.start()
        self.mock_process_iter = self.psutil_process_iter_patcher.start()

        process_attrs_as_dict = {
            'name': 'process_name',
            'pid': 1234,
            'username': 'user',
            'cmdline': '/usr/bin/process_name',
        }

        process_attrs = {
            'memory_info_ex.return_value': mock.Mock(rss=1048576),
            'num_threads.return_value': 1,
            'num_fds.return_value': 1,
            'cpu_percent.return_value': 1,
            'io_counters.return_value': mock.Mock(**{'read_count': 1,
                                                     'write_count': 1,
                                                     'read_bytes': 1024,
                                                     'write_bytes': 1024})
        }
        process = mock.Mock(**process_attrs)
        process.as_dict.return_value = process_attrs_as_dict
        self.mock_process_iter.return_value = [process]
        self.mock_process.return_value = process

        config = {'init_config': {},
                  'instances': [{'name': 'test',
                                 'search_string': ['process_name'],
                                 'detailed': True}]}
        self.check = load_check('process', config)

    def tearDown(self):
        self.psutil_process_patcher.stop()
        self.psutil_process_iter_patcher.stop()

    def testPidCount(self):
        self.check.run()
        metrics = self.check.get_metrics()

        self.assertGreater(len(metrics), 1)

    def run_check(self):
        self.check.prepare_run()
        self.check.run()
        metrics = self.check.get_metrics()

        measurement_names = [metric['measurement']['name'] for metric in metrics]

        measurement_names.sort()
        return measurement_names

    def testMeasurements(self):
        measurement_names = self.run_check()

        # first run will not have cpu_perc in it
        expected_names = ['process.io.read_count',
                          'process.io.read_kbytes',
                          'process.io.write_count',
                          'process.io.write_kbytes',
                          'process.mem.rss_mbytes',
                          'process.open_file_descriptors',
                          'process.pid_count',
                          'process.thread_count']

        self.assertListEqual(measurement_names, expected_names)

        # run again to get cpu_perc
        expected_names.insert(0, 'process.cpu_perc')
        measurement_names = self.run_check()
        self.assertListEqual(measurement_names, expected_names)
