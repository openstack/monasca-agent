import os
import psutil
import unittest

from tests.common import load_check


class TestSimpleProcess(unittest.TestCase):
    def setUp(self):
        p = psutil.Process(os.getpid())
        config = {'init_config': {}, 'instances': [{'name': 'test',
                                                    'search_string': [p.name()],
                                                    'detailed': False}]}
        self.check = load_check('process', config)

    def testPidCount(self):
        self.check.run()
        metrics = self.check.get_metrics()
        self.assertTrue(len(metrics) == 1, metrics)
        self.assertTrue(metrics[0].name == 'process.pid_count')


class TestDetailedProcess(unittest.TestCase):
    def setUp(self):
        p = psutil.Process(os.getpid())
        config = {'init_config': {}, 'instances': [{'name': 'test',
                                                    'search_string': [p.name()],
                                                    'detailed': True}]}
        self.check = load_check('process', config)

    def testPidCount(self):
        self.check.run()
        metrics = self.check.get_metrics()
        self.assertTrue(len(metrics) > 1, metrics)

    def run_check(self):
        self.check.prepare_run()
        self.check.run()
        metrics = self.check.get_metrics()

        measurement_names = []
        for metric in metrics:
            measurement_names.append(metric.name)

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

        self.assertEquals(measurement_names, expected_names)

        # run again to get cpu_perc
        expected_names.insert(0, 'process.cpu_perc')
        measurement_names = self.run_check()
        self.assertEquals(measurement_names, expected_names)
