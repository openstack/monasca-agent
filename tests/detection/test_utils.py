# Copyright 2017 FUJITSU LIMITED
# Copyright 2017 OP5 AB
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
from unittest import mock

from oslotest import base
from oslo_config import cfg

from monasca_setup.detection import utils


class TestDetectionUtilsOsloConf(base.BaseTestCase):
    PROJECT = 'foo'
    PROG = 'bar'

    @mock.patch('monasca_setup.detection.utils.cfg.ConfigOpts')
    def test_load_oslo_configuration_no_args(self, config_opts):
        config_opts.return_value = co = mock.Mock()
        opts = [
            {'opt': cfg.StrOpt('region_name')}
        ]
        args = ['python', 'foo-api']

        self._run_load_oslo_test(co, opts, args)

    @mock.patch('monasca_setup.detection.utils.cfg.ConfigOpts')
    def test_load_oslo_configuration_with_args(self, config_opts):
        config_opts.return_value = co = mock.Mock()
        opts = [
            {'opt': cfg.StrOpt('region_name')}
        ]
        args = ['python', 'foo-api', '--config-file', '/foo/bar/file',
                '--config-dir', '/foo/bar']

        self._run_load_oslo_test(co, opts, args)

    def test_should_create_new_oslo_conf_for_each_call(self):
        # test ensures that each call for load_oslo_configuration
        # creates new object of oslo_config.ConfigOpts
        cfg_1 = utils.load_oslo_configuration(
                from_cmd=[],
                in_project=self.PROJECT,
                of_prog=self.PROG,
                for_opts=[]
        )
        cfg_2 = utils.load_oslo_configuration(
                from_cmd=[],
                in_project=self.PROJECT,
                of_prog=self.PROG,
                for_opts=[]
        )

        self.assertIsNot(cfg_1, cfg_2)

    def test_distinct_oslo_confs_should_contain_different_opts(self):
        # test ensures that each instance created via load_oslo_configuration
        # contains different values of the same opts

        file_1, file_2 = self.create_tempfiles([('', ''), ('', '')])
        base_dir = os.path.dirname(file_1)
        os.makedirs(base_dir + '/1')
        os.makedirs(base_dir + '/2')

        cmd_1 = ['python', 'test', '--config-dir', base_dir + '/1']
        cmd_2 = ['python', 'test', '--config-dir', base_dir + '/2']
        cmd_3 = ['python', 'test', '--config-file', file_1]
        cmd_4 = ['python', 'test', '--config-file', file_2]

        opts = [
            {'opt': cfg.StrOpt('region_name')}
        ]

        cfg_1 = utils.load_oslo_configuration(
                from_cmd=cmd_1,
                in_project=self.PROJECT,
                of_prog=self.PROG,
                for_opts=opts
        )
        cfg_2 = utils.load_oslo_configuration(
                from_cmd=cmd_2,
                in_project=self.PROJECT,
                of_prog=self.PROG,
                for_opts=opts
        )
        cfg_3 = utils.load_oslo_configuration(
                from_cmd=cmd_3,
                in_project=self.PROJECT,
                of_prog=self.PROG,
                for_opts=opts
        )
        cfg_4 = utils.load_oslo_configuration(
                from_cmd=cmd_4,
                in_project=self.PROJECT,
                of_prog=self.PROG,
                for_opts=opts
        )

        self.assertIsNot(cfg_1, cfg_2)
        self.assertIsNot(cfg_3, cfg_4)
        self.assertNotEqual(cfg_1, cfg_2)
        self.assertNotEqual(cfg_3, cfg_4)

    def test_just_keep_built_in_options(self):
        # test ensures that non built-in oslo.config options to
        # load_oslo_configuration is skipped

        cmd_1 = ['python', 'test']
        cmd_2 = ['python', 'test', '--log-file', '/var/log/test/test.log']

        opts = [
            {'opt': cfg.StrOpt('region_name')}
        ]

        cfg_1 = utils.load_oslo_configuration(
            from_cmd=cmd_1,
            in_project=self.PROJECT,
            of_prog=self.PROG,
            for_opts=opts
        )
        cfg_2 = utils.load_oslo_configuration(
            from_cmd=cmd_2,
            in_project=self.PROJECT,
            of_prog=self.PROG,
            for_opts=opts
        )

        self.assertIsNot(cfg_1, cfg_2)
        self.assertEqual(cfg_1, cfg_2)

    def test_parsing_different_command_styles(self):
        # test ensures that options sent to load_oslo_configuration with
        # different command styles generates the same output

        cmd_1 = ['python', 'test', '--config-dir', '.']
        cmd_2 = ['python', 'test', '--config-dir=.']

        opts = [
            {'opt': cfg.StrOpt('region_name')}
        ]

        cfg_1 = utils.load_oslo_configuration(
            from_cmd=cmd_1,
            in_project=self.PROJECT,
            of_prog=self.PROG,
            for_opts=opts
        )
        cfg_2 = utils.load_oslo_configuration(
            from_cmd=cmd_2,
            in_project=self.PROJECT,
            of_prog=self.PROG,
            for_opts=opts
        )

        self.assertIsNot(cfg_1, cfg_2)
        self.assertEqual(cfg_1, cfg_2)

    def _run_load_oslo_test(self, config_opts, opts, args):
        actual_args = args[2:]

        conf = utils.load_oslo_configuration(
                from_cmd=args,
                in_project=self.PROJECT,
                of_prog=self.PROG,
                for_opts=opts
        )

        self.assertIsNotNone(conf)

        for opt in opts:
            config_opts.register_opt.assert_called_once_with(**opt)
        config_opts.assert_called_once_with(
                args=actual_args,
                project=self.PROJECT,
                prog=self.PROG
        )
