# -*- coding: latin-1 -*-

import mock
import os.path
import tempfile
import unittest

from monasca_agent.common import config
from monasca_agent.common.config import Config
from monasca_agent.common import util


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

        p = util.PidFile(program, pid_dir)

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
            self.assertTrue(util.is_valid_hostname(hostname), hostname)

        for hostname in not_valid_hostnames:
            self.assertFalse(util.is_valid_hostname(hostname), hostname)

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

    @mock.patch.object(Config, '_read_config')
    @mock.patch('monasca_agent.common.util.get_parsed_args')
    def testConfigFromParsedArgs(self, mock_parsed_args, mock_read_config):
        mock_options = mock.Mock()
        mock_parsed_args.return_value = (mock_options, mock.sentinel.args)
        conf = Config()
        # object is singleton, for this case, it needs to be reloaded.
        conf.__init__()

        self.assertEqual(mock_options.config_file, conf._configFile)

    @mock.patch.object(Config, '_read_config')
    @mock.patch('monasca_agent.common.util.get_parsed_args')
    @mock.patch('monasca_agent.common.config.os')
    def testConfigFileFromDefault(self, mock_os, mock_parsed_args, mock_read_config):
        mock_os.path.exists = mock.create_autospec(mock_os.path.exists, return_value=True)
        mock_options = mock.Mock()
        mock_options.config_file = None
        mock_parsed_args.return_value = (mock_options, mock.sentinel.args)
        conf = Config()
        # object is singleton, for this case, it needs to be reloaded.
        conf.__init__()

        self.assertEqual(config.DEFAULT_CONFIG_FILE, conf._configFile)
        mock_os.path.exists.assert_called_once_with(config.DEFAULT_CONFIG_FILE)

    def test_verify_common_config_opts(self):
        opts = util.get_parsed_args(prog='test')
        opts_dict = vars(opts[0])
        self.assertItemsEqual(['config_file', 'clean', 'verbose'],
                              opts_dict.keys())
