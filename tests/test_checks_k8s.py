import os
import time

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
                                                              'gauges': ['messages_avg'],
                                                              'rates': ['messages_total'],
                                                              'dimensions': {
                                                                  'simple_dimension': 'simple_label',
                                                                  'complex_dimension': {
                                                                      'source_key': 'complex_label',
                                                                      'regex': 'k8s_([._\-a-zA-Z0-9]*)_postfix'
                                                                  }
                                                              },
                                                              'groups': {
                                                                  'testgroup': {
                                                                      'rates': ['responses_. *']
                                                                  }
                                                                  # dimensions should be inherited from above
                                                              }}}]}
        self.check = load_check('process', self._config)
        self.helper = DynamicCheckHelper(self.check, 'dynhelper')

    def run_check(self):
        self.check.run()
        self.helper.push_metric(self._config['instances'][0], metric='responses_ok', value=10.0, group="testgroup",
                                labels={'simple_label': 'simple_label_test',
                                        'complex_label': 'k8s_monasca-api-a8109321_postfix'})
        self.helper.push_metric(self._config['instances'][0], metric='messages_avg', value=5.0,
                                labels={'simple_label': 'simple_label_test',
                                        'complex_label': 'k8s_monasca-api-a8109321_postfix'})
        self.helper.push_metric(self._config['instances'][0], metric='messages_total', value=1)
        time.sleep(1)
        self.helper.push_metric(self._config['instances'][0], metric='responses_ok', value=15.0, group="testgroup",
                                labels={'simple_label': 'simple_label_test',
                                        'complex_label': 'k8s_monasca-api-a8109321_postfix'})
        self.helper.push_metric(self._config['instances'][0], metric='messages_total', value=100)
        metrics = self.check.get_metrics()

        return metrics

    def testMeasurements(self):
        metrics = self.run_check()
        for m in metrics:
            print "metric: {0}, dimensions: {1}".format(m.name, repr(m.dimensions))
        metric1 = filter(lambda m: m.name == 'dynhelper.messages_avg', metrics)
        metric2 = filter(lambda m: m.name == 'dynhelper.messages_total', metrics)
        metric3 = filter(lambda m: m.name == 'dynhelper.testgroup.responses_ok', metrics)
        self.assertTrue(len(metric1) > 0,
                        'gauge dynhelper.messages_avg missing in metric list {0}'.format(repr(metrics)))
        self.assertEquals(metric1[0].dimensions,
                          {'simple_dimension': 'simple_label_test', 'complex_dimension': 'monasca-api-a8109321',
                           'hostname': metric1[0].dimensions.get('hostname')})
        self.assertTrue(len(metric2) > 0,
                        'rate dynhelper.messages_total missing in metric list {0}'.format(repr(metrics)))
        self.assertEquals(metric2[0].dimensions,
                          {'hostname': metric2[0].dimensions.get('hostname')})
        self.assertTrue(len(metric3) > 0,
                        'rate dynhelper.responses_ok missing in metric list {0}'.format(repr(metrics)))
        self.assertEquals(metric3[0].dimensions,
                          {'simple_dimension': 'simple_label_test', 'complex_dimension': 'monasca-api-a8109321',
                           'hostname': metric3[0].dimensions.get('hostname')})
