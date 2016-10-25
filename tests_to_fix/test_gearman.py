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
