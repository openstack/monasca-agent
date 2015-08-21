import unittest

from tests.common import load_check


class TestSimpleProcess(unittest.TestCase):
    def setUp(self):
        config = {'init_config': {}, 'instances': [{'name': 'test',
                                                   'search_string': ['python'],
                                                   'detailed': False}]}
        self.check = load_check('process', config)

    def testPidCount(self):
        self.check.run()
        metrics = self.check.get_metrics()
        self.assertTrue(len(metrics) == 1, metrics)
        self.assertTrue(metrics[0].name == 'process.pid_count')


class TestDetailedProcess(unittest.TestCase):
    def setUp(self):
        config = {'init_config': {}, 'instances': [{'name': 'test',
                                                   'search_string': ['python'],
                                                   'detailed': True}]}
        self.check = load_check('process', config)

    def testPidCount(self):
        self.check.run()
        metrics = self.check.get_metrics()
        self.assertTrue(len(metrics) > 1, metrics)

    def testMeasurements(self):
        self.check.run()
        metrics = self.check.get_metrics()

        measurement_names = []
        for metric in metrics:
            measurement_names.append(metric.name)

        measurement_names.sort()

        expected_names = ['process.cpu_perc',
                          'process.involuntary_ctx_switches',
                          'process.io.read_count',
                          'process.io.read_kbytes',
                          'process.io.write_count',
                          'process.io.write_kbytes',
                          'process.mem.real_mbytes',
                          'process.mem.rss_mbytes',
                          'process.mem.vsz_mbytes',
                          'process.open_file_descriptors',
                          'process.open_file_descriptors_perc',
                          'process.pid_count',
                          'process.thread_count',
                          'process.voluntary_ctx_switches']
        self.assertTrue(measurement_names == expected_names)
