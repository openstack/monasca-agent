import unittest
from tests.common import load_check
import time


class TestMySql(unittest.TestCase):

    def setUp(self):
        # This should run on pre-2.7 python so no skiptest
        self.skip = False
        try:
            import pymysql
        except ImportError:
            self.skip = True

    def testChecks(self):
        if not self.skip:
            agent_config = {'mysql_server': 'localhost',
                            'mysql_user': "datadog",
                            'mysql_pass': "phQOrbaXem0kP8JHri1qSMRS",
                            'version': '0.1',
                            'api_key': 'toto'}

            # Initialize the check from checks_d
            c = load_check('mysql', {'init_config': {}, 'instances': {}}, agent_config)
            conf = c.parse_agent_config(agent_config)
            self.check = load_check('mysql', conf, agent_config)

            self.check.run()
            metrics = self.check.get_metrics()
            self.assertTrue(len(metrics) >= 8, metrics)
            time.sleep(1)
            self.check.run()
            metrics = self.check.get_metrics()
            self.assertTrue(len(metrics) >= 16, metrics)

if __name__ == '__main__':
    unittest.main()
