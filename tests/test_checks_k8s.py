import os
import psutil
import unittest

from monasca_agent.collector.checks.utils import DynamicCheckHelper
from tests.common import load_check


class TestDynamicCheckHelper(unittest.TestCase):
    def setUp(self):
        p = psutil.Process(os.getpid())
        self._config = {'init_config': {}, 'instances': [{'name': 'test',
                                                    'search_string': [p.name()],
                                                    'detailed': True,
                                                    'mapping': {
                                                        'dimensions': {
                                                            'simple_dimension': 'simple_label',
                                                            'complex_dimension': {
                                                                'source_key': 'complex_label',
                                                                'regex': 'k8s_([a-zA-Z_\-\.]*)_postfix'
                                                            }
                                                        }
                                                    }}]}
        self.check = load_check('process', self._config)
        self.helper = DynamicCheckHelper(self.check, 'dynhelper')

    def run_check(self):
        self.check.run()
        self.helper.push_metric(self._config['instances'][0], metric='messages_avg', value=5.0, labels={'simple_label': 'simple_label_test', 'complex_label': 'k8s_monasca-api-a8109321_postfix'})
        self.check.run()
        metrics = self.check.get_metrics()

        return metrics

    def testMeasurements(self):
        metrics = self.run_check()
        for m in metrics:
            print "metric: {0}, dimensions: {1}".format(m.name, repr(m.dimensions))
        metric1 = filter(lambda m: m.name == 'dynhelper.messages_avg', metrics)
        self.assertTrue(len(metric1) > 0, 'metric dynhelper.messages_avg missing in metric list {0}'.format(repr(metrics)))
        self.assertEquals(metric1[0].dimensions, { 'simple_dimension': 'simple_label_test', 'complex_dimension': 'monasca-api-a8109321' } )