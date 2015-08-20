# -*- coding: latin-1 -*-
import unittest
import os.path
import tempfile

from monasca_agent.common.config import Config
from monasca_agent.common.util import PidFile, is_valid_hostname


class TestConfig(unittest.TestCase):

    def xtestWhiteSpaceConfig(self):
        """Leading whitespace confuse ConfigParser
        """
        agent_config = Config.get_config(
            cfg_path=os.path.join(os.path.dirname(os.path.realpath(__file__)), "badconfig.conf"))
        self.assertEqual(agent_config["api_key"], "1234")

    def testGoodPidFie(self):
        """Verify that the pid file succeeds and fails appropriately"""

        pid_dir = tempfile.mkdtemp()
        program = 'test'

        expected_path = os.path.join(pid_dir, '%s.pid' % program)
        pid = "666"
        pid_f = open(expected_path, 'w')
        pid_f.write(pid)
        pid_f.close()

        p = PidFile(program, pid_dir)

        self.assertEqual(p.get_pid(), 666)
        # clean up
        self.assertEqual(p.clean(), True)
        self.assertEqual(os.path.exists(expected_path), False)

    def testHostname(self):
        valid_hostnames = [
            u'i-123445',
            u'5dfsdfsdrrfsv',
            u'432498234234A'
            u'234234235235235235',  # Couldn't find anything in the RFC saying it's not valid
            u'A45fsdff045-dsflk4dfsdc.ret43tjssfd',
            u'4354sfsdkfj4TEfdlv56gdgdfRET.dsf-dg',
            u'r' * 255,
        ]

        not_valid_hostnames = [
            u'abc' * 150,
            u'sdf4..sfsd',
            u'$42sdf',
            u'.sfdsfds'
            u's™£™£¢ª•ªdfésdfs'
        ]

        for hostname in valid_hostnames:
            self.assertTrue(is_valid_hostname(hostname), hostname)

        for hostname in not_valid_hostnames:
            self.assertFalse(is_valid_hostname(hostname), hostname)

    def testConfigIsSingleton(self):
        # create a temp conf file
        tempdir = tempfile.mkdtemp()
        conf_file = os.path.join(tempdir, 'agent.yaml')
        with open(conf_file, 'wb') as fd:
            fd.write(
                """
                Logging:
                  collector_log_file: /var/log/monasca/agent/collector.log
                  forwarder_log_file: /var/log/monasca/agent/forwarder.log
                  log_level: DEBUG
                  statsd_log_file: /var/log/monasca/agent/statsd.log
                Main:
                  check_freq: 60
                  dimensions: {}
                  hostname: example.com
                """
            )
        conf_1 = Config(configFile=conf_file)
        conf_2 = Config(configFile=conf_file)
        conf_3 = Config()
        self.assertTrue(conf_1 is conf_2)
        self.assertTrue(conf_1 is conf_3)


if __name__ == '__main__':
    unittest.main()
