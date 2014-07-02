import unittest
from tests.common import load_check
from nose.plugins.skip import SkipTest


class CouchDBTestCase(unittest.TestCase):

    def testMetrics(self):
        raise SkipTest('Require CouchDB')
        config = {
            'instances': [{
                'server': 'http://localhost:5984',
            }]
        }
        agent_config = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.check = load_check('couch', config, agent_config)

        self.check.check(config['instances'][0])

        metrics = self.check.get_metrics()
        self.assertTrue(isinstance(metrics, list), metrics)
        self.assertTrue(len(metrics) > 3)
        self.assertTrue(
            len([k for k in metrics if "instance:http://localhost:5984" in k[3]['dimensions']]) > 3)
