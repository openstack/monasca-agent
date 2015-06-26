import os
import shutil
import unittest
import uuid

from common import get_check


class TestCrash(unittest.TestCase):

    def setUp(self):
        self.crash_dir = '/tmp/crash-test-%s' % str(uuid.uuid4())
        os.mkdir(self.crash_dir)

    def tearDown(self):
        shutil.rmtree(self.crash_dir)

    def test_checks(self):
        config = """
init_config:
   crash_dir: %s

instances:
   - name: crash_stats
""" % self.crash_dir

        (check, instances) = get_check('crash', config)

        # Baseline check
        check.check(instances[0])
        metrics = check.get_metrics()
        self.assertEqual(metrics[0].value, 0)
        self.assertEqual(metrics[0].value_meta['latest'], '')

        # Add a crash and re-check
        os.mkdir(os.path.join(self.crash_dir,'201504141011'))

        check.check(instances[0])
        metrics = check.get_metrics()
        self.assertEqual(metrics[0].value, 1)
        self.assertEqual(metrics[0].value_meta['latest'],
                         '2015-04-14 10:11:00')

        # Add a second crash and re-check
        os.mkdir(os.path.join(self.crash_dir,'201505222303'))

        check.check(instances[0])
        metrics = check.get_metrics()
        self.assertEqual(metrics[0].value, 2)
        self.assertEqual(metrics[0].value_meta['latest'],
                         '2015-05-22 23:03:00')


if __name__ == "__main__":
    unittest.main()
